#!/usr/bin/env python

import sys, os, re
from cachetools import cached
import subprocess

num_re = r'\[([0-9]+.?[0-9]*)\]'

replaced_number_postfix = '[-]'
image_postfix = '[Twine.image]'
valid_postfixes = {replaced_number_postfix, image_postfix}


def display_untweeability(dir):
	"""
	Given a directory containing subdirectories of twine games, display which ones can be decompiled to Twee
	return: list of paths to files that can be untweed
	"""
	total, valid = 0, 0
	untweeable_paths = []

	for subdir in os.listdir(dir):
		path = os.path.join(dir, subdir)
		if os.path.isdir(path):
			html, filename = get_html_source(path)
			can_be_untweed = is_untweeable(html)
			if can_be_untweed:
				untweeable_paths.append(os.path.join(path, filename))
			total += 1
			valid += 1 if can_be_untweed else 0
			print(path, can_be_untweed)

	print(f'{valid} of {total} untweeable ({valid/total*100 if total != 0 else 0}%)')
	return untweeable_paths


def get_html_source(dir):
	"""
	Get the first html file from a directory and return its content
	"""
	html_files = [f for f in os.listdir(dir) if f.endswith('.html')]
	html_file = html_files[0] if html_files else None
	html = open(os.path.join(dir, html_file)).read() if html_file else ''
	return html, html_file


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
	Determine if a given .tw file is valid
	"""

	passages = split_passages(twee)
	return \
		all([is_valid_passage(p) for p in passages]) \
		and contains_start(passages)


def is_valid_passage(passage):
	"""
	Determine if a given passage can compile
	"""
	passage = passage.strip()
	lines = split_lines(passage)

	valid_prefix = lines[0].startswith('::')
	valid_name = re.search(r'::(.*) \[?(.*)]?', lines[0])
	valid_postfix = any(lines[0].endswith(post) for post in valid_postfixes)

	return valid_prefix and valid_name and valid_postfix


def contains_start(passages):
	return any([is_start(p) for p in passages])


def is_start(passage):
	return False


def clean_numbers(passage, repl='-'):
	"""
	Remove passage numbers: [1] -> [-]
	"""
	lines = split_lines(passage)
	lines[0] = re.sub(num_re, '[' + repl + ']', lines[0])
	return '\n'.join(lines)


def re_number(passages, repl='-'):
	"""
	Order passages - add passage numbers back to the de-numbered passages
	"""
	repl = '\[' + repl + '\]'
	i = 1
	new_passages = []
	for p in passages:
		p_lines = split_lines(p)
		if p_lines[0].endswith(repl):
			p_lines[0] = p_lines[0].replace(repl, '[' + str(i) + ']')
			i += 1
		new_passages.append('\n'.join(p_lines))
	return new_passages


def clean_images(twee):
	"""
	Remove images from a .tw file.
	"""
	twee = re.sub(r'data:image/(.*)', '\n', twee)
	twee = re.sub(r'\[img\[(.*)\]\](.*)\n', '\n', twee)
	twee = re.sub(r'(.*)\[Twine.image\]\n', '\n', twee)

	return twee


def split_passages(twee):
	passages = twee.split('::')
	for passage in passages[1:]:
		passage = passage.strip()
		yield '::' + passage


def unsplit_passages(passages):
	return '\n\n'.join(passages)


@cached(cache={})  # cache passages that have already been split to reducce compute time
def split_lines(passage):
	return passage.split('\n')


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
	untwee_all(argv[0], argv[1])


def untwee_all(source_html_dir, write_twee_to):
	"""Take all twee games in source_html_dir and write them as twee files to the write_twee_to_directory"""
	untweeable_files = display_untweeability(source_html_dir)
	for path in untweeable_files:
		name = path.split('/')[-2]
		html, error = untwee(path)
		with open(os.path.join(write_twee_to, name) + '.tw', 'wb') as w:
			w.write(html)


def untwee(html_path):
	untwee_cmd = f"twee/untwee {html_path}"  # launch untwee (python2 script) using bash
	process = subprocess.Popen(untwee_cmd.split(), stdout=subprocess.PIPE)
	html, error = process.communicate()  # receive output from the python2 script
	html = html.strip()
	print(html, error)
	return html, error


def clean_twee(argv):
	file = open(argv[0])
	twee = file.read()
	twee = clean_images(twee)
	passages = order([p for p in split_passages(twee)])
	passages = [clean_numbers(p) for p in passages]
	passages = re_number([p for p in passages])
	twee = unsplit_passages(passages)
	print(twee)


if __name__ == '__main__':
	main(sys.argv[1:])
