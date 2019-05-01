# PyCASC
(This product is very unfinished and should not be used for anything other than entertainment/simple exports. Report any exceptions thrown in issues)
A Python3 CASC library and pyqt app 

This is part of a much larger month-long project, that will hopefully result in a very nice blizzard reverse-engineering toolkit.

## CASC? 
Blizzard's proprietary data storage format (used in practically all of their products)

## Why?
Dunno, was bored

## How do i use it?
As a library? You shouldn't do that right now, the public api is completely undocumented and I've only tested it on War3 (which differs greatly from WoW / other games)

As an app? You modify CASCViewApp.py at the very bottom, and change it to the directory of your WAR3 **(it may work for other games, but i'm not sure)** folder. And then run that file (assuming you have all of the packages in requirements.txt installed)

## What's the library do?
- Open a basic (currently war3 only) CASC filesystem
- List all files that exist in both the filesystem and the rootfile
- Read individual files (only Z-Lib and Plain currently supported as chunks)

## What's the app do?
Current features:
- Explore the file-tree of a CASC filesystem
- Export individual files one at a time
- View files as hexdumps
- View text-files as text files
- Open files externally, without having to export them.
- View very basic file/folder information (basically just file size)

Planned features:
- Folder exports ( export an entire file tree, with folder structure )
- DBC viewing & exporting as sql/csv ( Blizzard proprietary database format )
- BLP viewing & exporting ( Blizzard proprietary image format )
