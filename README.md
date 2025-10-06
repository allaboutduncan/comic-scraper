# Comic Scraper

A simple command-line tool to download comics from supported websites and save them as CBZ files (comic book archives).

## Supported Websites
- e-hentai.org
- readcomiconline.li

## Prerequisites

You need to have Python installed on your computer. This tool works on Windows, macOS, and Linux.

### Installing Python

**Windows:**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.10 or newer
3. Run the installer
4. ⚠️ **Important**: Check the box "Add Python to PATH" during installation

**macOS:**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.10 or newer
3. Run the installer

**Linux:**
Python is usually pre-installed. Open a terminal and check:
```bash
python3 --version
```
If not installed, use your package manager:
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip

# Fedora
sudo dnf install python3 python3-pip
```

## Installation

### Step 1: Clone or Download This Repository

**Option A: Using Git (Recommended)**

Open a terminal/command prompt and run:
```bash
git clone https://github.com/YOUR-USERNAME/comic-scrape.git
cd comic-scrape
```

**Option B: Download ZIP**

1. Click the green "Code" button at the top of this page
2. Click "Download ZIP"
3. Extract the ZIP file to a folder
4. Open a terminal/command prompt and navigate to that folder:
   - **Windows**: Open the folder in File Explorer, type `cmd` in the address bar, press Enter
   - **macOS**: Right-click the folder, hold Option key, click "Open Terminal Here"
   - **Linux**: Right-click the folder, click "Open in Terminal"

### Step 2: Install Dependencies

In the terminal/command prompt, run:

**Windows:**
```bash
pip install -r requirements.txt
playwright install chromium
```

**macOS/Linux:**
```bash
pip3 install -r requirements.txt
playwright install chromium
```

> **Note**: If you get a "permission denied" error on macOS/Linux, add `--user` to the pip command:
> ```bash
> pip3 install --user -r requirements.txt
> ```

This will download and install all the necessary libraries. It may take a few minutes.

## How to Use

### Step 1: Run the Script

In the terminal/command prompt (in the comic-scrape folder), run:

**Windows:**
```bash
python comic_scraper.py
```

**macOS/Linux:**
```bash
python3 comic_scraper.py
```

### Step 2: Choose Your Input Method

The script will ask:
```
Enter (1) for single URL or (2) for text file:
```

**Option 1 - Single URL:**
- Type `1` and press Enter
- Paste the comic URL and press Enter
- The script will download the comic

**Option 2 - Text File with Multiple URLs:**
- Create a text file (e.g., `urls.txt`) in the comic-scrape folder
- Add one URL per line in the file
- Type `2` and press Enter
- Enter the filename (e.g., `urls.txt`) and press Enter
- The script will download all comics in the list

### Step 3: Wait for Download

The script will:
1. Download all comic pages
2. Create a CBZ file (comic book archive)
3. Save it in the comic-scrape folder

You can open CBZ files with comic readers like:
- [Calibre](https://calibre-ebook.com/) (Windows, macOS, Linux)
- [CDisplayEx](https://www.cdisplayex.com/) (Windows)
- [Chunky](https://apps.apple.com/app/chunky-comic-reader/id663502260) (iOS)
- [Perfect Viewer](https://play.google.com/store/apps/details?id=com.rookiestudio.perfectviewer) (Android)

## Example

### Single URL Example:
```
Enter (1) for single URL or (2) for text file: 1
Enter URL: https://readcomiconline.li/Comic/Batman/Issue-1
```

### Text File Example:

Create a file called `urls.txt`:
```
https://readcomiconline.li/Comic/Batman/Issue-1
https://readcomiconline.li/Comic/Superman/Issue-1
https://e-hentai.org/g/123456/abcdef123/
```

Then run:
```
Enter (1) for single URL or (2) for text file: 2
Enter text file name (in current directory): urls.txt
```

## Troubleshooting

### "python is not recognized" (Windows)
Python is not in your PATH. Either:
- Reinstall Python and check "Add Python to PATH"
- Or use the full path: `C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe comic_scraper.py`

### "ModuleNotFoundError"
Dependencies aren't installed. Run the installation commands again:
```bash
pip install -r requirements.txt
playwright install chromium
```

### "Permission denied" (macOS/Linux)
Add `--user` to the pip install command:
```bash
pip3 install --user -r requirements.txt
```

### Downloads fail or are incomplete
- Check your internet connection
- Some sites may have rate limiting - try again later
- Make sure you're using the correct URL format

## Notes

- Downloaded CBZ files are saved in the same folder as the script
- The script will automatically handle duplicate filenames by adding numbers
- Be respectful of the websites - don't run too many downloads at once
- Some sites may require you to be logged in or have restrictions

## License

This tool is for personal use only. Respect copyright laws and website terms of service.
