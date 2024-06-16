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

release_codes = ['!','rev','alternate','v','beta','proto','alpha','promo','pirate','demo','sample','bootleg','o','b']

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
    def __init__(self, root_dir, delete, regions_preference):
        self.root_dir = root_dir
        self.delete = delete
        self.rank_table = self.build_table(regions_preference)
        self.roms = {}

    def get_roms(self):
        rom_list = 'roms.txt'
        if os.path.exists(rom_list):
            print('using cached list from: {}'.format(rom_list))
            with open(rom_list, 'r') as fd:
                game_list = [line.strip() for line in fd.readlines()]
        else:
            game_list = []
            for dirname, dirnames, filenames in os.walk(self.root_dir):
                # Modify dirnames in-place to skip 'images' and 'videos'
                dirnames[:] = [d for d in dirnames if d not in ['images', 'videos']]            
                # print path to all filenames.
                for filename in filenames:
                    aFile = os.path.join(dirname, filename)
                    game_list.append(aFile)
            with open(rom_list, 'w') as fd:
                for f in game_list:
                    fd.write('{}\n'.format(f))
        return game_list

    def add_rom(self, rom_obj):
        if rom_obj.stripped_filename not in self.roms:
            self.roms[rom_obj.stripped_filename] = {}
            self.roms[rom_obj.stripped_filename]['roms'] = []
        self.roms[rom_obj.stripped_filename]['roms'].append(rom_obj)
        
    def clean(self):
        tot_files = 0
        tot_size = 0
        unq_size = 0

        for stripped_filename, roms in self.roms.items():
            if len(roms['roms']) > 1:
                print(Fore.BLACK + Back.LIGHTWHITE_EX + stripped_filename + Style.RESET_ALL)
                have_marked = False
                delete_txt = Fore.GREEN + 'OK' + Style.RESET_ALL
                
                for r in sorted(roms['roms'], key=lambda x: (*x.build_rank(), x.region_rank(self.rank_table), x.timestamp_rank()), reverse=True):

                    print('\t:{}:{:.2f}MB:{}'.format(delete_txt, r.get_filesize_mb(), r.base_filename))
                    if have_marked is True and self.delete is True:
                        print('\tDeleting: {}'.format(r.full_path_filename))
                        os.remove(r.full_path_filename)
                    if have_marked is False:
                        unq_size += r.get_filesize_mb()
                        have_marked = True
                        delete_txt = Fore.RED + 'KO' + Style.RESET_ALL

                    #Calculate stats
                    tot_files += 1
                    tot_size += r.get_filesize_mb()
            else:
                #Calculate stats            
                tot_files += 1
                tot_size += roms['roms'][0].get_filesize_mb()
                unq_size += roms['roms'][0].get_filesize_mb()
                
        print('total unique files: {} ({:.2f}MB)'.format(len(self.roms),unq_size))
        print('total files       : {} ({:.2f}MB)'.format(tot_files, tot_size))

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
                raise ValueError("Invalid format: Unmatched parentheses or square brackets")
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
    
    # If build information is included in filename, use build type and
    # version (if provided) to score roms according to 'release_codes' order.
    def build_rank(self):
        
        build = float('inf')
        version = float('inf')
        
        pattern = r'\b((?:{}))\s*(\d*\.?\d*)\b'.format('|'.join(release_codes))
        regex = re.compile(pattern)

        for tag in self.tokens:
            match = regex.search(tag.lower())
            if match:
                build = match.group(1)
                if len(match.groups()) == 2 and match.group(2):
                    version = float(match.group(2).lstrip('0'))
                break

        ranks = [(i,item) for i, item in enumerate(reversed(release_codes))]
        for score, rank in ranks:
            if rank == build:
                return (score, version)
        
        return (float('inf'), version)

# Parse command line args:
def parseArgs():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--regions', help='Preferences for sorting', default='U,E')
    parser.add_argument('--rom_dir', help='Location where your roms are stored', default='y://')
    parser.add_argument('--delete', help='WARNING: setting this will delete the roms!', action='store_true')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    colorama_init()
    # parse args:
    args = parseArgs()
    # create the ROMSET class:
    romset = ROMSET(args.rom_dir, args.delete, [p.strip() for p in args.regions.split(',')])
    # get the list of games:
    game_list = romset.get_roms()
    # create a rom object for each file:
    for full_path_filename in game_list:
        romset.add_rom(Rom(full_path_filename))
    print('Bag of tags:')
    print(list(sorted(bag_tags)))
    romset.clean()
    print('all done!')
