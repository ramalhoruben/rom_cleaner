import os, sys, re, argparse
from functools import reduce
from dateutil.parser import parse
from datetime import datetime
from colorama import Fore, Style, Back
from colorama import init as colorama_init

bag_tags = set()

country_codes = {
    'As':'Asia', 'A': 'Australia', 'B': 'Brazil', 'C': 'Canada', 'Ch':'China', 'D': 'Netherlands', 'E':'Europe', 'F':'France',
    'Fn': 'Finland', 'G': 'Germany', 'Gr': 'Greece', 'Hk': 'Hong Kong', 'I': 'Italy','J':'Japan','K':'Korea','Nl':'Netherlands',
    'No':'Norway', 'R': 'Russia', 'S': 'Spain', 'Sw': 'Sweden', 'U': 'USA', 'UK': 'United Kingdom', 'W': 'World', 
    'Unl': 'Unlicensed', 'PD': 'Public Domain', 'Unk': 'Unknown'
}

release_codes = ['!','rev','alternate','alt','v','o','beta','proto','alpha','promo','pirate','demo','sample','bootleg','b']
    
def valid_brackets(filename):
    """ Validate that the filename has matching parentheses or brackets. """
    stack = []
    matching_bracket = {')': '(', ']': '['}
    
    for char in filename:
        if char in '([':
            stack.append(char)
        elif char in ')]':
            if not stack or stack.pop() != matching_bracket[char]:
                return False
    return not stack
    
class ROMSET():
    def __init__(self, root_dir, regions, ignore_dirs):
        self.root_dir = root_dir
        self.rank_table = self.build_table([p.strip() for p in regions.split(',')])
        self.titles = {}
        self.roms_txt = 'roms.txt'
        self.ignore_dirs = [p.strip() for p in ignore_dirs.split(',')]

    def get_roms(self):

        if os.path.exists(self.roms_txt):
            print('using cached list from: {}'.format(self.roms_txt))
            with open(self.roms_txt, 'r') as fd:
                rom_list = [line.strip() for line in fd.readlines()]
        else:
            rom_list = []
            for dirname, dirnames, filenames in os.walk(self.root_dir):
                # Modify dirnames in-place to skip ignore dirs
                dirnames[:] = [d for d in dirnames if d not in self.ignore_dirs]            
                # print path to all filenames.
                for filename in filenames:
                    aFile = os.path.join(dirname, filename)
                    rom_list.append(aFile)
            with open(self.roms_txt, 'w') as fd:
                for f in rom_list:
                    fd.write('{}\n'.format(f))
        return rom_list

    def add_rom(self, rom_obj):
        if rom_obj.stripped_filename not in self.titles:
            self.titles[rom_obj.stripped_filename] = {}
            self.titles[rom_obj.stripped_filename]['roms'] = []
        self.titles[rom_obj.stripped_filename]['roms'].append(rom_obj)

    def clean(self, delete=False):

        tot_files = 0
        tot_size = 0
        unq_size = 0

        for stripped_filename, title in sorted(self.titles.items()):

            # Multiple roms for same title
            if len(title['roms']) > 1:

                print(Fore.BLACK + Back.LIGHTWHITE_EX + stripped_filename + Style.RESET_ALL)

                is_main = True
                main = None
                
                for rom in sorted(title['roms'], key=lambda x: (*x.build_rank(), x.region_rank(self.rank_table), \
                    x.timestamp_rank(),-x.get_disc_number()), reverse=True):                

                    # Check if active rom is part of main rom.
                    if not is_main:
                        is_part_of_main = rom.is_part_of_main_of(main)

                    # Choose action to display for active rom.
                    if is_main or is_part_of_main: action = Fore.GREEN + 'OK' + Style.RESET_ALL
                    else: action = Fore.RED + 'KO' + Style.RESET_ALL

                    print('\t:{}:{:.2f}MB:{}'.format(action, rom.get_filesize_mb(), rom.base_filename))

                    if not is_main and not is_part_of_main and delete:
                        print('\tDeleting: {}'.format(rom.full_path_filename))
                        os.remove(rom.full_path_filename)
                    if is_main:
                        unq_size += rom.get_filesize_mb()
                        is_main = False
                        main = rom

                    #Calculate stats
                    tot_files += 1
                    tot_size += rom.get_filesize_mb()
                    
            # Singleton
            else:
                #Calculate stats            
                tot_files += 1
                tot_size += title['roms'][0].get_filesize_mb()
                unq_size += title['roms'][0].get_filesize_mb()
        
        # Remove rom list to force rebuilding an updated list on next run.
        if delete and os.path.exists(self.roms_txt):
            os.remove(self.roms_txt)
            
        print('total unique titles: {} ({:.2f}MB)'.format(len(self.titles),unq_size))
        print('total roms         : {} ({:.2f}MB)'.format(tot_files, tot_size))        

    # Build a table to rank title region according to supplied
    # preferences, or else according to alphabetic order.
    def build_table(self, user_ccs):
        
        # Check if priority country codes is valid
        for cc in user_ccs:
            found=False
            for cc2 in country_codes.items():
                if cc in cc2:  found=True
            if found==False:
                raise ValueError("Must be a valid country code, code is case sensitive.")
        
        alpha_rank = [(i, item) for i, item in enumerate(sorted(set(country_codes) - set(user_ccs),reverse=True))]
        return alpha_rank + [(i,item) for i, item in enumerate(reversed(user_ccs),start=len(alpha_rank))]


class Rom():
    def __init__(self, full_path_filename):

        self.full_path_filename = full_path_filename
        self.base_filename, \
        self.filesize, \
        self.stripped_filename, \
        self.tokens = self.describe_rom(full_path_filename)

    # Helper function:
    def find(self, s, ch):
        return [i for i, ltr in enumerate(s) if ltr == ch]

    # Extraction tags:
    def describe_rom(self, full_path_filename):
        
        base_filename = os.path.basename(full_path_filename)
        filesize = os.path.getsize(full_path_filename)

        # Strip filename of brackets and contents
        stripped_filename = re.sub(r'[\[\(].*?[\]\)]', '', base_filename).strip()
        # Also remove any leftover spaces before file extension
        stripped_filename = re.sub(r'\s+\.', '.', stripped_filename)

        def extract_brackets_content(filename):
            """ Extract content within parentheses and square brackets using regular expressions. """
            # Patterns to match content within parentheses and square brackets
            pattern_parentheses = re.compile(r'\(([^()]+)\)')
            pattern_brackets = re.compile(r'\[([^\[\]]+)\]')
            
            # Find all matches
            matches_parentheses = pattern_parentheses.findall(filename)
            matches_brackets = pattern_brackets.findall(filename)
            
            return matches_parentheses + matches_brackets
            
        def extract_tags(filename):
            if not valid_brackets(filename):
                print("Invalid format: Unmatched parentheses or square brackets for file:\n"+filename)
                sys.exit(1)
            else:
                rom_tags = []
                brackets_contents = extract_brackets_content(filename)
                if brackets_contents:
                    per_bracket_tags = map(lambda s: set([tag.strip() for tag in s.split(',')]),brackets_contents)
                    rom_tags = list(sorted(reduce(set.union, per_bracket_tags)))
                
                return rom_tags

        tags = extract_tags(base_filename)

        global bag_tags
        bag_tags = bag_tags.union(tags)

        return base_filename, filesize, stripped_filename, tags

    def get_filesize_mb(self):
        return self.filesize / (1024.0 ** 2)
   
    # Deduce rom region or regions based on filename tags
    def get_romregions(self):
    
        countries = []
        for tag in self.tokens:
            for k, v in country_codes.items():
                if tag in (k,v) : countries.append(k)
        
        if len(countries):
            return countries
        else: return 'Unk'
        
    def tag_isvolume(self, tag):
        valid_parts = ['disk', 'disc', 'side', 'volume']
        pattern = r'^({})\s+(\w+)'.format('|'.join(valid_parts))
        regex = re.compile(pattern)
        match = regex.search(tag.lower())
        if match:
            part_type = match.group(1) 
            part_val = match.group(2)
            # Check if numeric or not, some roms use ascii (A, B..) for sequence
            if part_val.isnumeric(): part_num= int(part_val)
            elif len(part_val)==1: part_num = ord(part_val[0])
            else:
                print('Unknown disc sequence, change to numbers to proceed.')
                sys.exit(1)
            
            return (part_type, int(part_num))
        return None

    def get_disc_number(self):
    
        for tag in self.tokens:
            v_info = self.tag_isvolume(tag)
            if v_info: return v_info[1]
        return -1
                
    def has_multiple_disc(self):
        #Found at least one ocorrence where disc numbers started at 0
        return self.get_disc_number() >= 0
    
    # Returns true if roms differ from each other only by volume information
    def is_part_of_main_of(self, rom):
        if not rom.has_multiple_disc() or not self.has_multiple_disc(): return False
        if rom.get_disc_number() == self.get_disc_number(): return False        
        else:
            # Calculate tag diffbuild_rankerences between roms 
            differences = set(rom.tokens) ^ set(self.tokens)
            return all([self.tag_isvolume(tag) for tag in differences])        

    # If build information is included in filename, use build type and
    # version (if provided) to score roms according to 'release_codes' order.
    def build_rank(self):
        
        # '!' should have higher priority than no build informatin whatsoever
        build = len(release_codes) - 2
        version = float('inf')
        
        escaped_release_codes = [re.escape(code) for code in release_codes]
        
        # Create a regex pattern dynamically
        # Adding word boundaries for most release codes
        # Special handling for release codes that are just special characters (!)
        escaped_release_codes_with_boundaries = [r'\b' + code for code in escaped_release_codes if code.isalnum()]
        escaped_special_codes = [code for code in escaped_release_codes if not code.isalnum()]        
        
        pattern = r'^((?:{}))\s*(\d*\.?\d*)'.format('|'.join(escaped_release_codes_with_boundaries + escaped_special_codes))        
        regex = re.compile(pattern)
        
        for tag in self.tokens:
            match = regex.search(tag.lower())
            if match:
                build = match.group(1)
                if len(match.groups()) == 2 and match.group(2):
                    version = float(match.group(2).lstrip('0'))
                break
                
        # Build ranking table according to release_codes order
        ranks = [(i,item) for i, item in enumerate(reversed(release_codes))]
        for score, rank in ranks:
            if rank == build:
                return (score, version)
        return (build, version)

    # Rank rom according to tagged region(s) and user preferences
    def region_rank(self,rank_table):
                
        def score_rom(rom_ccs):
            result = []
            for item in rank_table:
                if item[1] in rom_ccs:
                    result.append(item[0])
            return result
    
        rom_ccs = self.get_romregions()       
        return max(score_rom(rom_ccs))
    
    # If a timestamp is included capture it to resolve ties, if no timestamp
    # was supplied assume it is the most recent build
    def timestamp_rank(self):

        for tag in self.tokens:
            try:
                return parse(tag)
            except (ValueError, OverflowError):
                continue
        return datetime.max
    
# Parse command line args:
def parseArgs():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--regions', help='Preferences for sorting: USA, Europe, case sensistive.', default='U,E')
    parser.add_argument('--rom_dir', help='Location where your roms are stored.', default='y://')
    parser.add_argument('--ignore_dirs', help='List of subdirectories to ignore', default='images,videos,manuals')
    parser.add_argument('--delete', help='WARNING: setting this will delete the roms!', action='store_true')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    colorama_init()
    # parse args:
    args = parseArgs()
    # create the ROMSET class:
    romset = ROMSET(args.rom_dir, args.regions, args.ignore_dirs)
    # get the list of games:
    rom_list = romset.get_roms()
    # create a rom object for each file:
    for full_path_filename in rom_list:
        romset.add_rom(Rom(full_path_filename))

    print('rehearsing rom cleanse...')
    romset.clean()
    if(args.delete):
        print('now deleting...')
        romset.clean(args.delete)
    print('all done!')
