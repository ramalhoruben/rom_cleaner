# rom_cleaner
Trim Game Roms based on File Name

I take no responsibility for the usage of this script!

When you run it with the --delete flag, it WILL delete ROMs!

Make a backup of your ROMs before using the --delete flag!

This is a simple script that will go through your ROM collection, and propose removal of duplicate titles based on their file name.

It is guaranteed to keep 1 (and only 1) ROM of each title, except when the candidate title has multiple volume, where 
all related volumes will be kept.

For instance (this is safe to run... you need to explicity put the **--delete** flag actually delete stuff.)

```bash
python clean_roms.py --regions U,E --rom_dir /roms/snes
...
Solomon's Key 2.nes
	:OK:0.25MB:Solomon's Key 2 (Europe).nes
	:KO:0.25MB:Solomon's Key 2 (USA) (Beta).nes
...
Joshua & the Battle of Jericho.nes
	:OK:0.25MB:Joshua & the Battle of Jericho (USA) (v6.0) (Unl).nes
	:KO:0.25MB:Joshua & the Battle of Jericho (USA) (v5.0) (Unl).nes
...
Drip.nes
	:OK:0.28MB:Drip (World) (Proto) (2021-05-25) (Unl).nes
	:KO:0.28MB:Drip (World) (Proto) (2016-06-01) (Unl).nes
	:KO:0.26MB:Drip (World) (Proto) (2009-06-26) (Unl).nes
...
```
Games are ranked first according to the reported build, for example a revision is ranked higher than a beta, which
in turn is ranked higher than a alpha. Between different revisions or versions their number is used to break ties.

The second ranking criteria is game region, which by default prioritizes USA and European titles, region preference is customized through 
the --regions argument.

The third ranking criteria is timestamp, mostly used to sort between prototypes and betas.

```
usage: clean_roms.py [-h] [--regions REGIONS] [--rom_dir ROM_DIR] [--ignore_dirs IGNORE_DIRS] [--delete]

options:
  -h, --help            show this help message and exit
  --regions REGIONS     Preferences for sorting: USA, Europe, case sensistive. (default: U,E)
  --rom_dir ROM_DIR     Location where your roms are stored. (default: y://)
  --ignore_dirs IGNORE_DIRS
                        List of subdirectories to ignore (default: images,videos,manuals)
  --delete              WARNING: setting this will delete the roms! (default: False)
```

The script it's geared towards English, but feel free to modify it:

When you are happy with list of "KO" (aka, the files that the script will delete), run with the delete flag:

```bash
python clean_roms.py --regions U,E --rom_dir /Volumes/roms -- --delete
```
