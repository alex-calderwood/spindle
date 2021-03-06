#!/usr/bin/env python
import sys, os, re
from cachetools import cached
import subprocess
import zipfile
import shutil
import random
import strbalance

num_re = r'\[([0-9]+.?END[0-9]*)\]'

image_postfix = '[Twine.image]'

formats = shutil.get_unpack_formats()
valid_zip_extensions = []
for f in formats:
	valid_zip_extensions += f[1]

# Set to true if you are training on a small model like GPT-2
# A big model would be something like GPT-3
SMALL = False
NL = '<|nl|>'
BEGIN = '<|bg|>'
END = '<|ef|>'
BEGIN = BEGIN if SMALL else '<|begin|>'
NL = NL if SMALL else '<newline>'
END = END if SMALL else '<|end|>'
ENDCONTEXT = '<|title|>'
ENDPROMPT = '<|start|>'

balance_pairs = [
	['<<', '>>'],
	# ['<', '>'],
	# ['[[', ']]'],
	['[', ']'],
]

# Characters that must not occur within a passage's outgoing links.
# TODO the parenthesis make is such that previous() links are dissalowed, and this should be allowed in the future
INVALID_LINK_CHARACTERS = '.|[]()<>,*/\\\"\''
INVALID_PASSAGE_CHARACTERS = '@'

# https://dan-q.github.io/twee2/documentation.html
SPECIAL_PASSAGES = [
	'StoryTitle', 'StorySubtitle', 'StoryAuthor', 'StoryMenu',
	'StorySettings', 'StoryIncludes', 'Annotations', 'audio sources'
]

balancer = strbalance.Balance(pairs=balance_pairs, custom=True)


def display_untweeability(dir):
	"""
	Given a directory containing subdirectories of twine games, display which ones can be decompiled to Twee
	return: list of paths to files that can be untweed
	"""
	total, valid = 0, 0
	untweeable_paths = []

	for subdir in os.listdir(dir):
		path = os.path.join(dir, subdir)
		html, filename = get_html_source(path)
		can_be_untweed = is_untweeable(html)
		if can_be_untweed:
			untweeable_paths.append(filename)
		total += 1
		valid += 1 if can_be_untweed else 0
		print(path, can_be_untweed)

	print(f'{valid} of {total} untweeable ({valid/total*100 if total != 0 else 0}%)')
	return untweeable_paths


def lower_case_links(passage):
	"""
	The current model only supports lowercase links, so we need to process them here.
	"""

	def replacement(match):
		text = match.group(1)
		(text, link) = text.split('|') if '|' in text else ('', text)
		link = link.lower()
		text = text + '|' if text else ''
		return f"[[{text}{link}]]"

	return re.sub(r'\[\[(.*?)]]', replacement, passage)


@cached(cache={})  # cache passages that have already been split to reduce compute time
def get_links(passage):
	"""
	Given a twee passage, return the list of pages it links to.

	[[A Linked Passage]] -> A Linked Passage
	"""

	links = re.findall(r'\[\[(.*?)]]', passage)
	links = [link for link in links]
	links = [(l.split('|')[-1] if '|' in l else l) for l in links]

	choice_links = re.findall(r'<< ?choice ?\"(.*)\" ?>>', passage)
	choice_links = [l.group(1) for l in choice_links]

	return dedupe_in_order(links + choice_links)


def dedupe_in_order(in_list, dont_add=set()):
	"""
	Deduplicate the in_list, maintaining order
	:param dont_add: an additional stoplist
	"""
	dedupe = set() | dont_add
	ordered_deduped = []
	for l in in_list:
		if l not in dedupe:
			ordered_deduped.append(l)
			dedupe.add(l)
	return ordered_deduped


def init_twee(title, author):
	text = make_title("StoryTitle", process=False, line_end='\n')
	text += title + '\n'
	text += '\n'
	text += make_title("StoryAuthor", process=False, line_end='\n')
	text += author + '\n\n'
	return text


def unzip_all(dir, destination):
	for file in os.listdir(dir):
		path = os.path.join(dir, file)
		dest = destination + file.split('.')[0]
		print(path, dest)
		try_unzip(path, dest)


def try_unzip(file, destination):
	if zipfile.is_zipfile(file):
		path, name = os.path.split(file)
		shutil.unpack_archive(file, destination)
		return destination
	return file


def make_temp_file(contents):
	path = f'../temporary_game_files/html_{random.uniform(1000000, 2000000)}'
	with open(path, 'w') as file:
		file.write(contents)
	return path


def delete_temp_file(filename):
	os.remove(filename)


def get_html_source(dir):
	"""
	Get the first html file from a directory and return its content
	If dir is actually an HTML file, return that

	* Important byproduct: if you call this multiple times, the previously returned files may be deleted by subsequent
	calls. We expect you to move them or deal with them before calling this again *
	"""
	temp_dir = f'../temporary_game_files/{random.uniform(1000000, 2000000)}/'
	if os.path.isdir(temp_dir):
		shutil.rmtree(temp_dir)

	try:
		dir = try_unzip(dir, temp_dir)
	except NotImplementedError as e:
		if os.path.isdir(temp_dir):
			shutil.rmtree(temp_dir)
		return ''

	if os.path.isdir(dir):
		html_files = [f for f in os.listdir(dir) if f.endswith('.html')]
		# TODO handle multiple HTML Files
		html_file = html_files[0] if html_files else None
		html_file = os.path.join(dir, html_file) if html_file else None
		html = read_html(html_file)
	elif os.path.exists(dir):
		html_file = dir  # Assume the thing is an html file
		try:
			html = open(dir, 'r').read()
		except Exception:
			html = ''
		if "</html>" not in html:
			html_file = None
			html = ''
	else:
		raise FileNotFoundError("Could not find " + dir)

	if os.path.isdir(temp_dir):
		shutil.rmtree(temp_dir)

	return html


def read_html(html_file):
	try:
		return str(open(html_file).read()) if html_file else ''
	except UnicodeDecodeError as e:
		return ''


def is_untweeable(html):
	"""
	I'm not sure at the moment what constitutes untweeable HTML, but if we don't find DVIS in tiddlywiki,
	that is a blocker
	"""
	# the same regex used in tiddlywiki
	divs_re = re.compile(
		r'<div id="storeArea"(.*)</html>',
		re.DOTALL
	)

	return bool(divs_re.search(html))


def is_valid_twee(twee):
	"""
	Determine if a given twee script can compile
	"""
	return all(valid_twee_indicators(twee).values())


def valid_twee_indicators(twee):
	"""
	Determine if a given .tw file is valid
	"""
	passages = split_passages(twee)
	all_valid_passages = all([is_valid_passage(p) for p in passages])
	start = contains_start(passages)
	return {
		'all_valid_passages': all_valid_passages,
		'start': start,
	}


def valid_passage_indicators(passage):
	passage = passage.strip()
	lines = split_lines(passage)

	valid_prefix = lines[0].startswith('::')
	balanced = not balancer.is_unbalanced(passage)
	# links = get_links(passage)
	# links_valid = all([is_valid_passage(passage) for l in links])
	# valid_name = bool(re.search(r'::(.*) \[?(.*)]?', lines[0]))
	return {
		'valid_prefix': valid_prefix,
		'balanced': balanced,
		# 'link_valid': link_valid,
		# 'valid_name': valid_name,
	}


def is_valid_passage(passage):
	"""
	Determine if a given passage can compile
	"""
	return all(valid_passage_indicators(passage).values())


def contains_start(passages):
	return any([is_start(p) for p in passages])


def get_start(passages):
	for passage in passages:
		if is_start(passage):
			return passage
	return None


def make_passage_dict(passages):
	"""
	Create a dictionary mapping title to passage
	:rtype a dict: key: title_text, value: full_passage
	"""
	return {title_to_text(get_title(split_lines(passage)), remove_tag=True): passage for passage in passages}


def make_title(passage_name, process=True, line_end=''):
	"""Make a valid page header from a name"""
	passage_name = passage_name.lower() if process else passage_name
	return f':: {passage_name}{line_end}'


@cached(cache={})  # cache passages that have already been split to reduce compute time
def split_lines(passage):
	return passage.split('\n')


def get_title(lines):
	return lines[0].strip()


def title_to_text(title, remove_tag=False):
	if remove_tag:
		match = re.search(r'::(.*?) ?\[(.*)]', title)
		if match:
			return match.group(1).strip()
	match = re.search(r'::(.+)', title)
	return match.group(1).strip() if match else ''


def passage_to_text(passage):
	"""
	Given a twee passage (without the title), return just the cleaned text, devoid of link markers '[' and <<choice>> macros.txt
	TODO reuse some code between this and get_links.
	"""
	# Can't figure out way to do this in one line, but I think its possible, and would be faster
	new_passage, subs = re.subn(r'\[\[([^\|]*?)]]', r'\1', passage)
	new_passage, _ = re.subn(r'\[\[([^\|]*?)\|(.*?)]]', r'\1', new_passage)
	new_passage, _ = re.subn(r'<< ?choice ?\"(.*)\" ?>> ?', '', new_passage)

	# Remove residual duplicate spaces
	new_passage, _ = re.subn(r"(\s)\1+", r"\1", new_passage)

	return new_passage


def twee_to_gen_format(twee):
	"""
	Change from twee text to the format we will be generationg
	"""
	gen = BEGIN + twee.replace('\n', NL) + END + '\n'
	return gen


def is_start(passage):
	# TODO do this better
	title = title_to_text(get_title(split_lines(passage)), remove_tag=True)
	return 'start' == str(re.sub(r'\s+', ' ', title.lower()))


def is_special_passage(passage):
	title = title_to_text(get_title(split_lines(passage)), remove_tag=True)
	text = str(re.sub(r'\s+', ' ', title.lower()))
	return any([text == s.lower() for s in SPECIAL_PASSAGES])


def clean_link_text(passage, links):
	for link in links:
		validated_link = validate_link_text(link)
		if validated_link:
			passage = passage.replace(link, validated_link)
			links.remove(link)
			links.append(validated_link)

	return passage, links


# TODO Don't thikn we need these, will delete soon
# def clean_numbers(passage, repl='-'):
# 	"""
# 	Remove passage numbers: [1] -> [-]
# 	"""
# 	lines = split_lines(passage)
# 	lines[0] = re.sub(num_re, '[' + repl + ']', lines[0])
# 	return '\n'.join(lines)

# def re_number(passages, repl='-'):
# 	"""
# 	Order passages - add passage numbers back to the de-numbered passages
# 	"""
# 	repl = '[' + repl + ']'
# 	i = 1
# 	new_passages = []
# 	for p in passages:
# 		p_lines = split_lines(p)
# 		if p_lines[0].endswith(repl):
# 			p_lines[0] = p_lines[0].replace(repl, '[' + str(i) + ']')
# 			i += 1
# 		new_passages.append('\n'.join(p_lines))
# 	return new_passages


def clean_images(twee):
	"""
	Remove images from a .tw file.
	"""
	twee = re.sub(r'data:image/(.*)\n', '\n', twee)
	twee = re.sub(r'\[img\[(.*)\]\](.*)\n', '\n', twee)
	twee = re.sub(r'(.*)\[Twine.image\]\n', '\n', twee)
	twee = re.sub(r'\[>img\[(.*?)]]', '', twee)

	return twee


def remove_invalid_chars_from_passage(passage_text):
	"""
	Return a cleaned passage if the passage is invalid.
	If the passage is valid, return None
	"""
	# Check if any of the characters are invalid
	bad_chars = [c for c in passage_text if c in INVALID_PASSAGE_CHARACTERS]
	if bad_chars:
		for b in set(bad_chars):
			passage_text = passage_text.replace(b, '')
	return passage_text


def validate_link_text(link):
	"""
	Return a validate link if the link is invalid.
	If the link is valid, return None

	# TODO if there are bad characters in a [['simple']] link, we should turn it into [['simple'|simple]]
	"""
	new_link = None
	# Check if any of the characters are invalid
	bad_chars = [c for c in link if c in INVALID_LINK_CHARACTERS]
	if bad_chars:
		new_link = link
		for b in set(bad_chars):
			new_link = new_link.replace(b, '')
	return new_link


def remove_html(twee):
	"""Remove remainiing HTML from the twee"""

	twee = re.sub(r'<html>(.*)</html>', '', twee)
	return twee


def remove_duplicate_newlines(twee):
	return re.sub(r'\n+', '\n', twee)


def make_prompt(title, context=''):
	"""
	input:
		a twee title ie
		:: titlename
	output:
		a twee title surounded by GPT-3 readable start/end tokens
		<begin tokens>:: titlename<end tokens>
	"""
	if context:
		context = context.strip() + ENDCONTEXT

	return BEGIN + context + title + ENDPROMPT


def make_completion(passage_without_title):
	"""
	input:
		'a passage containing [[links|link]], etc'
	output:
		' a passage containing [[links|link]], etc<end tokens>'

	The completion should always begin with a space.
	"""
	return " " + passage_without_title.replace('\n', NL).strip() + END


def twee_to_gen_format_2(twee):
	"""Prepare for GPT-3"""
	passages = [p for p in split_lines(twee)]
	title = passages[0]
	rest_of_passage = remove_duplicate_newlines(unsplit_passages(passages[1:]))
	return make_prompt(title), make_completion(rest_of_passage)


def gen_to_twee_format_2(prompt='', response=''):
	twee = prompt + response
	cleaned = twee.replace(BEGIN, '').replace(ENDPROMPT, '').replace(ENDCONTEXT, '').replace(END, '').replace(NL, '\n')
	return cleaned


def twee_to_gen_format_3(twee, context=''):
	"""
	Prepare for GPT-3 using context.
	"""
	lines = [p for p in split_lines(twee)]
	title = lines[0]
	rest_of_passage = remove_duplicate_newlines(unsplit_lines(lines[1:]))
	return make_prompt(title, context=context), make_completion(rest_of_passage)


def gen_to_twee_format_3(prompt='', response=''):
	"""
	Process the generated content from GPT-3
	"""
	bad_things = f'{re.escape(BEGIN)}|{re.escape(ENDPROMPT)}|{re.escape(ENDCONTEXT)}|{re.escape(END)}'
	prompt = re.subn(bad_things, '', prompt)[0].replace(NL, '\n')
	response = re.subn(bad_things, '', response)[0].replace(NL, '\n')

	nl = '\n' if prompt and response else ''
	twee = prompt + nl + response
	return twee


def gen_to_twee_format(gen):
	"""
	Change from the generated format back to twee
	"""
	twee = gen.replace(NL, '\n').replace(END, '').replace(BEGIN, '')
	return twee


def split_passages(twee):
	passages = twee.split('::')
	for passage in passages[1:]:
		passage = passage.strip()
		yield '::' + passage


def unsplit_passages(passages):
	return '\n\n'.join(passages)


def unsplit_lines(lines):
	return '\n'.join(lines)


def page_number(passage):
	n = re.search(num_re, passage.split('\n')[0])
	return n.group(1) if n else -1


def order(passages):
	return sorted(
		passages,
		key=lambda p: float(page_number(p))
	)

def main(argv):
	# file = open(argv[0])
	# twee = file.read()
	# html = get_html_source(argv[0])
	# display_untweeability(argv[0])
	# untwee_all(argv[0], argv[1])
	pass


def untwee_all(source_html_dir, write_twee_to):
	"""Take all twee games in source_html_dir and write them as twee files to the write_twee_to_directory"""
	untweeable_files = display_untweeability(source_html_dir)
	for path in untweeable_files:
		name = path.split('/')[-2]
		html, error = untwee(path)
		with open(os.path.join(write_twee_to, name) + '.tw', 'wb') as w:
			w.write(html)


def untwee(html_path, twee_exec='../twee/'):
	untwee_cmd = f"{twee_exec}untwee {html_path}"  # launch untwee (python2 script) using bash
	process = subprocess.Popen(untwee_cmd.split(), stdout=subprocess.PIPE)
	twee_text, error = process.communicate()  # receive output from the python2 script
	return twee_text.strip(), error


def twee(twee_path, twee_exec='../twee/'):
	twee_cmd = f"{twee_exec}twee {twee_path}"  # launch untwee (python2 script) using bash
	process = subprocess.Popen(twee_cmd.split(), stdout=subprocess.PIPE)
	html, error = process.communicate()  # receive output from the python2 script
	return html.strip(), error


def open_file(file):
	subprocess.call(f"open {file}", shell=True, stdout=subprocess.PIPE)


def clean_twee(twee):
	twee = clean_images(twee)
	passages = order([p for p in split_passages(twee)])
	# passages = [clean_numbers(p) for p in passages] # This actually turns out to be important
	passages = [remove_html(p) for p in passages if not is_empty_passage(p)]
	twee = unsplit_passages(passages)
	twee = remove_duplicate_newlines(twee)
	return twee


def is_empty_passage(passage):
	# TODO the last case better
	passage = passage.strip()
	top = split_lines(passage)[0]
	return not(bool(passage)) or passage == '::untitled passage' or '[stylesheet]' in top or '[script]' in top or '[twee2]' in top


def get_macros(twee):
	macros = re.findall(r'<<(.*?)>>', twee)
	return macros


def replace_obvious_macros(twee):
	twee = re.sub(r'<<begin>>', '[[begin]]', twee)
	return twee



def replace_macros(twee):
	twee = re.sub(r'<<(.*?)>> ?', '', twee)
	return twee

# TODO get rid of scripts :: \nThe day after the ceremony, flush with determination and new power, you called a meeting and told all the staff that student deaths <<replace "should be" "could be">>must be<<endreplace>> eliminated in the next year.\n\nYou were given a [[standing ovation.|unknown]]\n\n\n:: inlinecss [script]\nString.prototype.unDash = function()\n{\n\tvar s = this.split("-");\n\tif(s.length > 1)\n\t\tfor(var t=1; t < s.length; t++)\n\t\t\ts[t] = s[t].substr(0,1).toUpperCase() + s[t].substr(1);\n\tretur...


if __name__ == '__main__':
	main(sys.argv[1:])
