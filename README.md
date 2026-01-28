# signal-export: PDF friendly
Export/backup chats from the [Signal](https://www.signal.org/) [Desktop app](https://www.signal.org/download/) to Markdown and HTML files with attachments. Each chat is exported as an individual .md/.html file and the attachments for each are stored in a separate folder. Attachments are linked from the Markdown files and displayed in the HTML (pictures, videos, voice notes). This is forked from https://github.com/carderne/signal-export.

In this fork, I have made changes to the script to ensure PDF files can properly be generated from the output. This version of this script removes all pagination present in the original, for the sake of generating PDF's. It also re-renders emoji's in the HTML-output, so that webkit renders can successfully include emoji's in the output PDF; which is not possible with the original output.

Originally adapted from https://github.com/mattsta/signal-backup.

## 2026 Modernization
This codebase was modernized in January 2026 with assistance from Claude (Anthropic) to update dependencies and implement modern Python best practices:
- Migrated from unmaintained `pysqlcipher3` to actively maintained `sqlcipher3`
- Updated all dependencies to current versions (BeautifulSoup4 4.14+, Click 8.3+, Markdown 3.10+)
- Implemented proper Python logging module replacing global variables
- Added comprehensive type hints for better IDE support and code clarity
- Implemented context managers for proper file handling
- Improved pathlib usage for better cross-platform compatibility

All changes maintain backward compatibility and preserve existing functionality. The codebase now follows modern Python standards while keeping the same MIT license.  
This is currently the only known way to back-up Signal Desktop and also the only way to get some form of backup for iPhone/iOS users. Signal's developers have so far refused to give iOS users any means to export a back-up and they have shot down any attempts and all viable solutions; even when they were extraordinary safe solutions. Signal's developers have refused to offer an explanation as to why they wish to deny us any means of backing up our data, even when this can be done in a simple and secure way - even through AMB or on iCloud. It looks like, unfortunately, Signal wants to keep your iOS data hostage at all costs. So good news: if your Signal Desktop instance is in-sync with your iPhone, you can now at least create a backup to HTML and/or PDF files so that at least your message history is safe to some extent. (Note: from the time you started using Desktop. Anything before that time is not included.) Of course if you wish to upload this as a backup to a cloud service, then I strongly recommend uploading it in an encrypted container for your own safety - don't ever upload the plain-text HTML/PDF!

Please continue reading to find all installation instructions and instructions to generate PDF's.  
Everything comes as-is and comes with zero guarantees (of proper or safe operation). Using this tool, any commands or instructions is at your own risk. Do not rely on the output of these scripts and commands as your sole backup and double-check the output. Tool can stop working if Signal changes anything to Signal Desktop. Let's hope they don't make any blocking changes that keep us away from safeguarding our data. :) 

This is a work in progress, more convenience features and commands to automate the process will be added in the near future.  

&nbsp;
## Example
An export for a group conversation looks as follows:
```markdown
[2019-05-29, 15:04] Me: How is everyone?
[2019-05-29, 15:10] Aya: We're great!
[2019-05-29, 15:20] Jim: I'm not.
```

Images are attached inline with `![name](path)` while other attachments (voice notes, videos, documents) are included as links like `[name](path)` so a click will take you to the file.

This is converted to HTML at the end so it can be opened with any web browser. 
The stylesheet `.css` is still very basic but I'll get to it sooner or later.

&nbsp;
## Installation - SEMI-AUTOMATED (MacOS ONLY! (at this time))
- Open up the Terminal-app on your Mac and install [Homebrew](https://brew.sh) by copy/pasting this command and pressing enter:
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
It may at some point prompt you for the password of your Mac. Type it in and hit enter, note that you will NOT see anything happening whilst you type. No \*\*\*\*\* or anything.
- Now we're going to do the magic, please use the commands for your architecture (Intel/Apple):
- - For **INTEL** Mac-users: 
once this is all succesfully installed: to automatically download this script + dependencies and backup all your chats + also convert them to PDF; copy/paste this command to your Terminal and press enter:
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/liroyvh/signal-export/master/MacEasyInstall.sh)"
```
- - For **Apple Silicon (M1, M1 Pro, etc.)** Mac-users:
once this is all succesfully installed: to automatically download this script + dependencies and backup all your chats + also convert them to PDF; copy/paste and run (enter) these two commands in your Terminal one-by-one:
```
arch -x86_64 /bin/zsh --login
/bin/zsh -c "$(curl -fsSL https://raw.githubusercontent.com/liroyvh/signal-export/master/MacEasyInstall.sh)"
```
- Now let it do its thing. It can take several minutes and it might prompt you for your Mac's password again. If you have tons and tons of media it can actually take quite some time. Once it's done, a Finder window will open with all your conversations in folders. You can find the PDF copies in the "pdf" folder. 
- This is for first time use only, for future use (with new backups): jump to the "Usage" chapter.

&nbsp;
## Installation - MANUAL (MacOS and Linux)


First, clone and install requirements (preferably into a virtualenv):
```
git clone https://github.com/liroyvh/signal-export.git
cd signal-export
```

### For MacOS:
- Install [Homebrew](https://brew.sh).
- Install Python 3.9 or higher: `brew install python3`
- Install system dependencies: `brew install openssl sqlcipher wkhtmltopdf`
  - If it says permissions are wrong, run the commands it suggests.
- **NOTE for Apple Silicon (M1/M2/M3) Macs:** If you encounter errors, you may need to run in x86_64 compatibility mode:
  ```bash
  arch -x86_64 /bin/zsh --login
  ```
  Then run all subsequent commands from that shell.
- Install Python packages:
  ```bash
  pip3 install -r requirements.txt
  ```


### For Linux
First ensure Python 3.9+ is installed:
```bash
python3 --version  # Should show 3.9 or higher
# If not, install: sudo apt install python3.9 python3-pip
```

Install system dependencies:
```bash
sudo apt install libsqlcipher-dev libssl-dev sqlcipher wkhtmltopdf
```

If sqlcipher is not available in your package manager, clone and build it:
```bash
git clone https://github.com/sqlcipher/sqlcipher.git
cd sqlcipher
mkdir build && cd build
../configure --enable-tempstore=yes CFLAGS="-DSQLITE_HAS_CODEC" LDFLAGS="-lcrypto"
sudo make install
cd ../..
```

Install Python packages:
```bash
pip3 install -r requirements.txt
```

### For Windows
- Install Python 3.9 or higher from [python.org](https://www.python.org/downloads/)
  - Make sure to check "Add Python to PATH" during installation
- Download and install wkhtmltopdf from [wkhtmltopdf.org](https://wkhtmltopdf.org/downloads.html)
- Download SQLCipher from [SQLCipher downloads](https://www.zetetic.net/sqlcipher/sqlcipher-windows/)
  - Extract and add the directory to your PATH
- Install Python packages:
  ```cmd
  pip install -r requirements.txt
  ```

**Note:** Windows support is experimental. Some features may require WSL (Windows Subsystem for Linux).

&nbsp;
## Usage
The following should work, and exports all your conversations to a sub-directory named "EXPORT":
```bash
python3 sigexport.py EXPORT
```

Or with verbose logging to see detailed progress:
```bash
python3 sigexport.py --verbose EXPORT
```

### Common Issues and Solutions

**Apple Silicon (M1/M2/M3) Architecture Error:**
If you get an error about wrong architecture (arm64 instead of x86_64), switch your terminal to x86_64 compatibility mode:
```bash
arch -x86_64 /bin/zsh --login
python3 sigexport.py EXPORT
```

**Database Decryption Error:**
If you get `DatabaseError: file is not a database`, the tool will automatically try manual decryption. If that fails, ensure:
1. Signal Desktop is closed
2. You have the latest version of sqlcipher installed
3. Your Signal database is not corrupted

**Python Version Error:**
If you see "Python 3.9 or higher is required", upgrade your Python:
- macOS: `brew upgrade python3`
- Linux: `sudo apt install python3.9`
- Windows: Download from [python.org](https://www.python.org/downloads/)


The full options are below:
```
Usage: ./sigexport.py [OPTIONS] [DEST]

Options:
  -s, --source PATH  Path to Signal config and database
      --old PATH     Path to previous export to merge with
  -c, --chats "NAME"  Comma-separated chat names to include. These are contact names or group names
  --list-chats              List all available chats/conversations
  --old PATH         Path to previous export to merge with
  -o, --overwrite    Flag to overwrite existing output
  -m, --manual       Flag to manually decrypt the database
  -v, --verbose      Enable verbose output logging
  --help             Show this message and exit.
```

You can add `--source /path/to/source/dir/` if the script doesn't manage to find the Signal config location. Default locations per OS are below. The directory should contain a folder called `sql` with a `db.sqlite` inside it.
- Linux: `~/.config/Signal/`
- macOS: `~/Library/Application Support/Signal/`
- Windows: `~/AppData/Roaming/Signal/`

You can also use `--old /previously/exported/dir/` to merge the new export with a previous one. _Nothing will be overwritten!_ It will put the combined results in whatever output directory you specified and leave your previos export untouched. Exercise is left to the reader to verify that all went well before deleting the previous one.

## Convert to PDF

**Important Note:** wkhtmltopdf development has been discontinued, but the tool still works for most use cases.

### Using wkhtmltopdf (Recommended, but discontinued)
If you want to convert all conversations to PDF, run this command from within your "EXPORT" folder:

**macOS/Linux:**
```bash
mkdir -p pdf && find . -maxdepth 2 -name '*.html' -exec sh -c 'for f; do wkhtmltopdf --enable-local-file-access "$f" "./pdf/$(basename "$(dirname "$f")").pdf"; done' _ {} +
```

**Windows (PowerShell):**
```powershell
New-Item -ItemType Directory -Force -Path pdf
Get-ChildItem -Path . -Filter "*.html" -Recurse -Depth 1 | ForEach-Object {
    $pdfName = $_.Directory.Name + ".pdf"
    wkhtmltopdf --enable-local-file-access $_.FullName "pdf\$pdfName"
}
```

### Alternative: Using WeasyPrint (Modern alternative)
[WeasyPrint](https://weasyprint.org/) is an actively maintained alternative:

```bash
pip install weasyprint
cd EXPORT
mkdir -p pdf
for dir in */; do
    weasyprint "${dir}index.html" "pdf/$(basename "$dir").pdf"
done
```

**Note:** WeasyPrint may render emojis differently than wkhtmltopdf.

### Alternative: Using Playwright (Best quality)
For the best rendering quality, use [Playwright](https://playwright.dev/):

```bash
pip install playwright
playwright install chromium
cd EXPORT
mkdir -p pdf
python3 << 'EOF'
from playwright.sync_api import sync_playwright
from pathlib import Path

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for html in Path('.').glob('*/index.html'):
        pdf_name = f"pdf/{html.parent.name}.pdf"
        page.goto(f"file://{html.absolute()}")
        page.pdf(path=pdf_name)
    browser.close()
EOF
```

Enjoy! :)

## Requirements
- Python 3.10 or higher recommended (for type hint support)
- sqlcipher3 (Python library)
- sqlcipher (system-level dependency)
- wkhtmltopdf (for PDF conversion)
- BeautifulSoup4, Click, Markdown (installed via requirements.txt)

## Credits and License
This project is released under the **MIT License**.

**Original Authors:**
- Chris Arderne ([@carderne](https://github.com/carderne)) - Original signal-export
- Matt Stancliff ([@mattsta](https://github.com/mattsta)) - signal-backup (original adaptation source)

**Contributors:**
- Liroy van Hoewijk ([@liroyvh](https://github.com/liroyvh)) - PDF-friendly fork (2021-2022)
- Modernization assistance by Claude (Anthropic) - Dependency updates and Python best practices (2026)

See LICENSE file for full license text.
