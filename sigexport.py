#!/usr/bin/env python3

# Check Python version before imports
import sys
if sys.version_info < (3, 9):
    print("Error: Python 3.9 or higher is required")
    print(f"You are using Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("\nPlease upgrade Python:")
    print("  - Download from: https://www.python.org/downloads/")
    print("  - Or use: brew install python3 (macOS)")
    print("  - Or use: sudo apt install python3.9 (Linux)")
    sys.exit(1)

import json
import os
import shutil
import platform
from pathlib import Path
from datetime import datetime
import re
import logging
from typing import Optional

import click
from sqlcipher3 import dbapi2 as sqlcipher
import markdown
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


def check_apple_silicon() -> None:
    """Check if running on Apple Silicon and warn if in native ARM mode."""
    if sys.platform == "darwin" and platform.machine() == "arm64":
        logger.warning("=" * 70)
        logger.warning("WARNING: Running on Apple Silicon (M1/M2/M3) in native ARM mode")
        logger.warning("If you encounter errors with sqlcipher3, you may need to run in")
        logger.warning("x86_64 compatibility mode. To do this, run:")
        logger.warning("  arch -x86_64 /bin/zsh --login")
        logger.warning("Then run this script again from that shell.")
        logger.warning("=" * 70)
        logger.warning("")


def check_sqlcipher_cli() -> bool:
    """Check if sqlcipher CLI is available."""
    result = os.system("which sqlcipher > /dev/null 2>&1" if sys.platform != "win32" else "where sqlcipher > nul 2>&1")
    return result == 0


def source_location() -> Path:
    """Get OS-dependent source location."""

    home = Path.home()
    if sys.platform == "linux" or sys.platform == "linux2":
        source_path = home / ".config/Signal"
    elif sys.platform == "darwin":
        source_path = home / "Library/Application Support/Signal"
    elif sys.platform == "win32":
        source_path = home / "AppData/Roaming/Signal"
    else:
        logger.error(f"Unsupported platform: {sys.platform}")
        logger.error("Please manually specify Signal location using --source PATH")
        logger.error("The directory should contain 'sql/db.sqlite' and 'config.json'")
        sys.exit(1)

    return source_path


def copy_attachments(src: Path, dest: Path, conversations: dict, contacts: dict) -> None:
    """Copy attachments and reorganise in destination directory."""

    src_att = Path(src) / "attachments.noindex"
    dest = Path(dest)

    for key, messages in conversations.items():
        name = contacts[key]["name"]
        logger.info(f"\tCopying attachments for: {name}")
        # some contact names are None
        if name is None:
            name = "None"
        contact_path = dest / name / "media"
        contact_path.mkdir(exist_ok=True, parents=True)
        for msg in messages:
            try:
                attachments = msg["attachments"]
                if attachments:
                    date = datetime.fromtimestamp(msg["timestamp"] / 1000.0).strftime(
                        "%Y-%m-%d"
                    )
                    for i, att in enumerate(attachments):
                        try:
                            att[
                                "fileName"
                            ] = f"{date}_{i:02}_{att['fileName']}".replace(
                                " ", "_"
                            ).replace(
                                "/", "-"
                            )
                            # account for erroneous backslash in path
                            att_path = Path(att["path"]).as_posix()
                            shutil.copy2(
                                src_att / att_path, contact_path / att["fileName"]
                            )
                        except KeyError:
                            logger.info(
                                f"\t\tBroken attachment:\t{name}\t{att['fileName']}"
                            )
                        except FileNotFoundError:
                            logger.info(
                                f"\t\tAttachment not found:\t{name} {att['fileName']}"
                            )
            except KeyError:
                logger.info(f"\t\tNo attachments for a message: {name}")


def make_simple(dest: Path, conversations: dict, contacts: dict) -> None:
    """Output each conversation into a simple text file."""

    dest = Path(dest)
    for key, messages in conversations.items():
        name = contacts[key]["name"]
        logger.info(f"\tDoing markdown for: {name}")
        is_group = contacts[key]["is_group"]
        # some contact names are None
        if name is None:
            name = "None"

        with open(dest / name / "index.md", "a") as mdfile:
            for msg in messages:
                timestamp = (
                    msg["timestamp"]
                    if "timestamp" in msg
                    else msg["sent_at"]
                    if "sent_at" in msg
                    else None
                )

                if timestamp is None:
                    logger.info("\t\tNo timestamp or sent_at; date set to 1970")
                    date = "1970-01-01 00:00"
                else:
                    date = datetime.fromtimestamp(timestamp / 1000.0).strftime(
                        "%Y-%m-%d %H:%M"
                    )

                logger.info(f"\t\tDoing {name}, msg: {date}")

                try:
                    body = msg["body"]
                except KeyError:
                    logger.info(f"\t\tNo body:\t\t{date}")
                    body = ""
                if body is None:
                    body = ""
                body = body.replace("`", "")  # stop md code sections forming
                body += "  "  # so that markdown newlines

                sender = "No-Sender"
                if "type" in msg.keys() and msg["type"] == "outgoing":
                    sender = "Me"
                else:
                    try:
                        if is_group:
                            for c in contacts.values():
                                num = c["number"]
                                if num is not None and num == msg["source"]:
                                    sender = c["name"]
                        else:
                            sender = contacts[msg["conversationId"]]["name"]
                    except KeyError:
                        logger.info(f"\t\tNo sender:\t\t{date}")

                try:
                    attachments = msg["attachments"]
                    for att in attachments:
                        file_name = att["fileName"]
                        # some file names are None
                        if file_name is None:
                            file_name = "None"
                        path = Path("media") / file_name
                        path = Path(str(path).replace(" ", "%20"))
                        if path.suffix and path.suffix.split(".")[1] in [
                            "png",
                            "jpg",
                            "jpeg",
                            "gif",
                            "tif",
                            "tiff",
                        ]:
                            body += "!"
                        body += f"[{file_name}](./{path})  "
                    print(f"[{date}] {sender}: {body}", file=mdfile)
                except KeyError:
                    logger.info(f"\t\tNo attachments for a message: {name}, {date}")


def fetch_data(db_file: Path, key: str, manual: bool = False, chats: Optional[list[str]] = None) -> tuple[dict, dict]:
    """Load SQLite data into dicts."""

    contacts = {}
    convos = {}

    db_file_decrypted = db_file.parents[0] / "db-decrypt.sqlite"

    # Try automatic decryption first, fall back to manual if it fails
    if not manual:
        try:
            db = sqlcipher.connect(str(db_file))
            c = db.cursor()
            c2 = db.cursor()
            # param binding doesn't work for pragmas, so use a direct string concat
            for cursor in [c, c2]:
                cursor.execute(f"PRAGMA KEY = \"x'{key}'\"")
                cursor.execute("PRAGMA cipher_page_size = 4096")
                cursor.execute("PRAGMA kdf_iter = 64000")
                cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
                cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")

            # Test if decryption worked by attempting a simple query
            c.execute("SELECT count(*) FROM sqlite_master")
            c.fetchone()

        except sqlcipher.DatabaseError as e:
            logger.warning(f"Automatic decryption failed: {e}")
            logger.warning("Falling back to manual decryption mode...")
            manual = True

    if manual:
        # Check if sqlcipher CLI is available
        if not check_sqlcipher_cli():
            logger.error("sqlcipher CLI not found!")
            logger.error("Manual decryption requires the sqlcipher command-line tool.")
            logger.error("")
            logger.error("Installation instructions:")
            if sys.platform == "darwin":
                logger.error("  macOS: brew install sqlcipher")
            elif sys.platform == "linux" or sys.platform == "linux2":
                logger.error("  Linux: sudo apt install sqlcipher (or equivalent for your distro)")
            elif sys.platform == "win32":
                logger.error("  Windows: Download from https://www.zetetic.net/sqlcipher/")
            logger.error("")
            logger.error("Alternatively, try running without the --manual flag")
            sys.exit(1)

        if db_file_decrypted.exists():
            db_file_decrypted.unlink()
        logger.info("Using manual decryption via sqlcipher CLI...")
        command = (
            f'echo "'
            f"PRAGMA key = \\\"x'{key}'\\\";"
            f"ATTACH DATABASE '{db_file_decrypted}' AS plaintext KEY '';"
            f"SELECT sqlcipher_export('plaintext');"
            f"DETACH DATABASE plaintext;"
            f'" | sqlcipher {db_file}'
        )
        result = os.system(command)
        if result != 0:
            logger.error("Manual decryption failed.")
            logger.error("This could mean:")
            logger.error("  1. The database key is incorrect")
            logger.error("  2. The database file is corrupted")
            logger.error("  3. Signal Desktop version changed the encryption format")
            sys.exit(1)
        db = sqlcipher.connect(str(db_file_decrypted))
        c = db.cursor()
        c2 = db.cursor()

    query = "SELECT type, id, e164, name, profileName, members FROM conversations"
    if chats is not None:
        chats = '","'.join(chats)
        query = query + f' WHERE name IN ("{chats}") OR profileName IN ("{chats}")'

    try:
        c.execute(query)
    except sqlcipher.DatabaseError as e:
        logger.error(f"Failed to query database: {e}")
        logger.error("This usually means the database decryption failed.")
        logger.error("Possible solutions:")
        logger.error("  1. Ensure Signal Desktop is closed")
        logger.error("  2. Try running with the --manual flag")
        logger.error("  3. Verify the database file exists and is not corrupted")
        sys.exit(1)
    for result in c:
        logger.info(f"\tLoading SQL results for: {result[3]}")
        is_group = result[0] == "group"
        cid = result[1]
        contacts[cid] = {
            "id": cid,
            "name": result[3],
            "number": result[2],
            "profileName": result[4],
            "is_group": is_group,
        }
        if contacts[cid]["name"] is None:
            contacts[cid]["name"] = contacts[cid]["profileName"]
        convos[cid] = []

        if is_group:
            usable_members = []
            # Match group members from phone number to name
            if result[5] is None:
                logger.info("\tEmpty group.")
            else:
                for member in result[5].split():
                    c2.execute(
                        "SELECT name, profileName FROM conversations WHERE id=?",
                        [member],
                    )
                    for name in c2:
                        usable_members.append(name[0] if name else member)
                contacts[cid]["members"] = usable_members

    c.execute("SELECT json, conversationId " "FROM messages " "ORDER BY sent_at")
    for result in c:
        content = json.loads(result[0])
        cid = result[1]
        if cid and cid in convos:
            convos[cid].append(content)

    if db_file_decrypted.exists():
        db_file_decrypted.unlink()

    return convos, contacts


def fix_names(contacts: dict) -> dict:
    """Remove non-filesystem-friendly characters from names."""

    for key, item in contacts.items():
        contact_name = item["number"] if item["name"] is None else item["name"]
        if contacts[key]["name"] is not None:
            contacts[key]["name"] = "".join(x for x in contact_name if x.isalnum())

    return contacts


def create_html(dest: Path, msgs_per_page: int = 100) -> None:
    root = Path(__file__).resolve().parents[0]
    css_source = root / "style.css"
    css_dest = dest / "style.css"
    if os.path.isfile(css_source):
        shutil.copy2(css_source, css_dest)
    else:
        logger.warning(f"Stylesheet not found: {css_source}")
        logger.warning(f"HTML files will be created without styling.")
        logger.warning(f"You can add a stylesheet manually at: {css_dest}")

    md = markdown.Markdown()

    for sub in dest.iterdir():
        if sub.is_dir():
            name = sub.stem
            logger.info(f"\tDoing html for {name}")
            path = sub / "index.md"
            # touch first
            path.touch(exist_ok=True)
            with path.open() as f:
                lines = f.readlines()
            lines = lines_to_msgs(lines)
            last_page = int(len(lines) / msgs_per_page)

            with open(sub / "index.html", "w") as htfile:
                print(
                    "<!doctype html>"
                    "<html lang='en'><head>"
                    "<meta charset='utf-8'>"
                    f"<title>{name}</title>"
                    "<link rel=stylesheet href='../style.css'>"
                    "</head>"
                    "<body>"
                    "<style>"
                    "img.emoji {"
                    "height: 1em;"
                    "width: 1em;"
                    "margin: 0 .05em 0 .1em;"
                    "vertical-align: -0.1em;"
                    "}"
                    "</style>"
                    "<script src='https://cdn.jsdelivr.net/npm/twemoji@14.0.2/dist/twemoji.min.js?11.2'></script>"
                    "<script>window.onload = function () { twemoji.parse(document.body);}</script>",
                    file=htfile,
                )

                page_num = 0
                for i, msg in enumerate(lines):
                    if i % msgs_per_page == 0:
                        nav = ""
                        if i > 0:
                            nav += "&nbsp;"
                        nav += f"&nbsp;"
                        nav += "&nbsp;"
                        nav += "&nbsp;"
                        if page_num != 0:
                            nav += f"&nbsp;"
                        else:
                            nav += "&nbsp;"
                        nav += "</div><div class=next>"
                        if page_num != last_page:
                            nav += f"&nbsp;"
                        else:
                            nav += "&nbsp;"
                        nav += "</div></nav>"
                        print(nav, file=htfile)
                        page_num += 1

                    date, sender, body = msg
                    sender = sender[1:-1]
                    date, time = date[1:-1].replace(",", "").split(" ")
                    body = md.convert(body)

                    # links
                    p = r"(https{0,1}://\S*)"
                    template = r"<a href='\1' target='_blank'>\1</a> "
                    body = re.sub(p, template, body)

                    # images
                    soup = BeautifulSoup(body, "html.parser")
                    imgs = soup.find_all("img")
                    for im in imgs:
                        if im.get("src"):
                            temp = BeautifulSoup(figure_template, "html.parser")
                            src = im["src"]
                            temp.figure.div.label.div.img["src"] = src
                            temp.figure.label.img["src"] = src

                            alt = im["alt"]
                            temp.figure.label["for"] = alt
                            temp.figure.label.img["alt"] = alt
                            temp.figure.input["id"] = alt
                            temp.figure.div.label["for"] = alt
                            temp.figure.div.label.div.img["alt"] = alt
                            im.replace_with(temp)

                    # voice notes
                    voices = soup.select(r"a[href*=\.m4a]")
                    for v in voices:
                        href = v["href"]
                        temp = BeautifulSoup(audio_template, "html.parser")
                        temp.audio.source["src"] = href
                        v.replace_with(temp)

                    # videos
                    videos = soup.select(r"a[href*=\.mp4]")
                    for v in videos:
                        href = v["href"]
                        temp = BeautifulSoup(video_template, "html.parser")
                        temp.video.source["src"] = href
                        v.replace_with(temp)

                    cl = "msg me" if sender == "Me" else "msg"
                    print(
                        f"<div class='{cl}'><span class=date>{date}</span>"
                        f"<span class=time>{time}</span>",
                        f"<span class=sender>{sender}</span>"
                        f"<span class=body>{soup.prettify()}</span></div>",
                        file=htfile,
                    )
                print("</div>", file=htfile)
                print(
                    "<script>if (!document.location.hash){"
                    "document.location.hash = 'pg0';}</script>",
                    file=htfile,
                )
                print("</body></html>", file=htfile)


video_template = """
<video controls>
    <source src="src" type="video/mp4">
    </source>
</video>
"""

audio_template = """
<audio controls>
<source src="src" type="audio/mp4">
</audio>
"""

figure_template = """
<figure>
    <label for="src">
        <img load="lazy" src="src" alt="img">
    </label>
    <input class="modal-state" id="src" type="checkbox">
    <div class="modal">
        <label for="src">
            <div class="modal-content">
                <img class="modal-photo" loading="lazy" src="src" alt="img">
            </div>
        </label>
    </div>
</figure>
"""


def lines_to_msgs(lines: list[str]) -> list:
    p = re.compile(r"^(\[\d{4}-\d{2}-\d{2},{0,1} \d{2}:\d{2}\])(.*?:)(.*\n)")
    msgs = []
    for li in lines:
        m = p.match(li)
        if m:
            msgs.append(list(m.groups()))
        else:
            # Only append to existing message if we have at least one message
            if msgs:
                msgs[-1][-1] += li
            else:
                logger.warning(f"Skipping malformed line (no previous message): {li[:50]}...")
    return msgs


def merge_attachments(media_new: Path, media_old: Path) -> None:
    """Merge attachments from old export into new export."""
    if not media_old.exists():
        logger.info("\t\tNo old media directory to merge")
        return

    if not media_old.is_dir():
        logger.warning(f"\t\tOld media path is not a directory: {media_old}")
        return

    # Ensure new media directory exists
    media_new.mkdir(parents=True, exist_ok=True)

    try:
        for f in media_old.iterdir():
            if f.is_file():
                dest_file = media_new / f.name
                if not dest_file.exists():
                    shutil.copy2(f, media_new)
                else:
                    logger.info(f"\t\tSkipping existing file: {f.name}")
    except Exception as e:
        logger.warning(f"\t\tError merging attachments: {e}")


def merge_chat(path_new: Path, path_old: Path) -> None:
    """Merge chat messages from old export with new export."""
    if not path_old.exists():
        logger.info(f"\t\tOld chat file not found: {path_old.name}")
        return

    if not path_new.exists():
        logger.warning(f"\t\tNew chat file not found: {path_new.name}")
        return

    try:
        with path_old.open() as f:
            old = f.readlines()
        with path_new.open() as f:
            new = f.readlines()

        # Check if files are empty
        if not old:
            logger.info("\t\tOld chat file is empty")
            return
        if not new:
            logger.info("\t\tNew chat file is empty, using old only")
            with path_new.open("w") as f:
                f.writelines(old)
            return

        # Show preview of what we're merging
        try:
            a, b, c, d = old[0][:30], old[-1][:30], new[0][:30], new[-1][:30]
            logger.info(f"\t\tFirst line old:\t{a}")
            logger.info(f"\t\tLast line old:\t{b}")
            logger.info(f"\t\tFirst line new:\t{c}")
            logger.info(f"\t\tLast line new:\t{d}")
        except IndexError:
            logger.info("\t\tOne of the files has no messages")
            return

        old_msgs = lines_to_msgs(old)
        new_msgs = lines_to_msgs(new)

        if not old_msgs and not new_msgs:
            logger.warning("\t\tNo messages found in either file")
            return

        # Merge and deduplicate
        merged = old_msgs + new_msgs
        merged = [m[0] + m[1] + m[2] for m in merged]
        merged = list(dict.fromkeys(merged))  # Remove duplicates while preserving order

        logger.info(f"\t\tMerged {len(old_msgs)} old + {len(new_msgs)} new = {len(merged)} total messages")

        with path_new.open("w") as f:
            f.writelines(merged)

    except Exception as e:
        logger.error(f"\t\tError merging chat: {e}")
        logger.error(f"\t\tOld file: {path_old}")
        logger.error(f"\t\tNew file: {path_new}")


def merge_with_old(dest: Path, old: Path) -> None:
    """Merge old export with new export without overwriting."""
    if not old.exists():
        logger.error(f"Old export directory not found: {old}")
        logger.error("Cannot perform merge operation")
        sys.exit(1)

    if not old.is_dir():
        logger.error(f"Old export path is not a directory: {old}")
        sys.exit(1)

    if not dest.exists() or not dest.is_dir():
        logger.error(f"New export directory not found: {dest}")
        logger.error("Cannot perform merge operation")
        sys.exit(1)

    logger.info(f"Merging old export from: {old}")
    logger.info(f"Into new export at: {dest}")
    logger.info("")

    merged_count = 0
    skipped_count = 0

    for sub in dest.iterdir():
        if sub.is_dir():
            name = sub.stem
            dir_old = old / name

            if dir_old.is_dir():
                logger.info(f"\tMerging conversation: {name}")
                merge_attachments(sub / "media", dir_old / "media")
                path_new = sub / "index.md"
                path_old = dir_old / "index.md"
                merge_chat(path_new, path_old)
                merged_count += 1
            else:
                logger.info(f"\tSkipping {name} (not in old export)")
                skipped_count += 1
            print()

    logger.info(f"Merge complete: {merged_count} conversations merged, {skipped_count} skipped")


@click.command()
@click.argument("dest", type=click.Path(), default="output")
@click.option(
    "--source", "-s", type=click.Path(), help="Path to Signal source and database"
)
@click.option(
    "--chats",
    "-c",
    help="Comma-separated chat names to include. These are contact names or group names",
)
@click.option(
    "--list-chats",
    is_flag=True,
    default=False,
    help="List all available chats/conversations and then quit",
)
@click.option("--old", type=click.Path(), help="Path to previous export to merge with")
@click.option(
    "--overwrite",
    "-o",
    is_flag=True,
    default=False,
    help="Flag to overwrite existing output",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose output logging",
)
@click.option(
    "--manual",
    "-m",
    is_flag=True,
    default=False,
    help="Whether to manually decrypt the db",
)
def main(
    dest,
    old=None,
    source=None,
    overwrite=False,
    verbose=False,
    manual=False,
    chats=None,
    list_chats=None,
):
    """
    Read the Signal directory and output attachments and chat files to DEST directory.
    Assumes the following default directories, can be overridden wtih --source.

    Default for DEST is a sub-directory output/ in the current directory.

    \b
    Default Signal directories:
     - Linux: ~/.config/Signal
     - macOS: ~/Library/Application Support/Signal
     - Windows: ~/AppData/Roaming/Signal
    """

    if verbose:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        logger.info("Verbose logging enabled")
        logger.info("")

    # Check for Apple Silicon and warn if needed
    check_apple_silicon()

    # Show what we're doing
    print("Signal Export Tool - PDF Friendly")
    print("=" * 50)

    if source:
        src = Path(source)
    else:
        src = source_location()
    source = src / "config.json"
    db_file = src / "sql" / "db.sqlite"

    logger.info(f"Signal directory: {src}")
    logger.info(f"Database: {db_file}")
    logger.info(f"Output: {dest}")
    if manual:
        logger.info("Mode: Manual decryption")
    logger.info("")

    if chats:
        chats = chats.split(",")

    # Read sqlcipher key from Signal config file
    if not source.is_file():
        logger.error(f"Signal config file not found: {source}")
        logger.error(f"Searched in directory: {src}")
        logger.error("")
        logger.error("Possible solutions:")
        logger.error("  1. Ensure Signal Desktop is installed and has been run at least once")
        logger.error("  2. Use --source to specify the correct Signal directory")
        logger.error("  3. Check that the path contains 'config.json' and 'sql/db.sqlite'")
        sys.exit(1)

    try:
        with open(source, "r") as conf:
            config_data = json.loads(conf.read())

            # Try different possible key names (Signal has changed this over time)
            key = None
            possible_keys = ["key", "encryptionKey", "safeStorageKey", "encrypted_key"]

            for key_name in possible_keys:
                if key_name in config_data:
                    key = config_data[key_name]
                    logger.info(f"Found encryption key using field: '{key_name}'")
                    break

            if key is None:
                logger.error("Could not find encryption key in config.json")
                logger.error(f"Config file: {source}")
                logger.error(f"Available fields: {list(config_data.keys())}")
                logger.error("")
                logger.error("This may indicate:")
                logger.error("  1. Signal has changed its config file format")
                logger.error("  2. Your Signal installation is corrupted")
                logger.error("  3. You need to update this tool")
                logger.error("")
                logger.error("Please report this issue with the available fields listed above")
                sys.exit(1)

            # Validate key format (should be a hex string)
            if not isinstance(key, str) or len(key) < 32:
                logger.warning(f"Encryption key seems unusually short or invalid (length: {len(key)})")
                logger.warning("This may cause decryption to fail")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config file as JSON: {e}")
        logger.error(f"Config file: {source}")
        logger.error("The config.json file appears to be corrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error reading config file: {e}")
        logger.error(f"Config file: {source}")
        sys.exit(1)

    # Check if database file exists
    if not db_file.is_file():
        logger.error(f"Signal database not found: {db_file}")
        logger.error(f"Expected location: {src / 'sql' / 'db.sqlite'}")
        logger.error("")
        logger.error("Possible solutions:")
        logger.error("  1. Ensure Signal Desktop is installed and has been run at least once")
        logger.error("  2. Use --source to specify the correct Signal directory")
        logger.error("  3. Close Signal Desktop if it's currently running")
        sys.exit(1)

    logger.info(f"\nFetching data from {db_file}\n")
    convos, contacts = fetch_data(db_file, key, manual=manual, chats=chats)

    if list_chats:
        names = sorted(v["name"] for v in contacts.values() if v["name"] is not None)
        print("\n".join(names))
        sys.exit()

    dest = Path(dest).expanduser()
    if not dest.is_dir():
        dest.mkdir(parents=True)
    elif overwrite:
        logger.warning(f"Overwriting existing directory: {dest}")
        shutil.rmtree(dest)
        dest.mkdir(parents=True)
    else:
        logger.error(f"Output directory already exists: {dest}")
        logger.error("")
        logger.error("Options:")
        logger.error("  1. Use --overwrite to replace the existing export")
        logger.error("  2. Use --old to merge with the existing export")
        logger.error("  3. Specify a different output directory")
        sys.exit(1)

    contacts = fix_names(contacts)
    print("\nCopying and renaming attachments")
    copy_attachments(src, dest, convos, contacts)
    print("\nCreating markdown files")
    make_simple(dest, convos, contacts)
    if old:
        print(f"\nMerging old at {old} into output directory")
        print("No existing files will be deleted or overwritten!")
        merge_with_old(dest, Path(old))
    print("\nCreating HTML files")
    create_html(dest)

    print(f"\nDone! Files exported to {dest}.\n")


if __name__ == "__main__":
    main()
