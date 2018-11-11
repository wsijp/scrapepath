#!/usr/bin/env python3

from bs4 import BeautifulSoup, Comment
from bs4.element import NavigableString
import copy
from util import *
import dateutil.parser as dparser
import re
import os
from urllib.parse import urljoin
import dateparser
import json
import sys

# TODO: Single item lists get absorbed into parent also inside forchild loop?? keep single item lists
# TODO: check whether re in tag attr works!

# ISSUES: NEVER USE THE SAME NAME TO RECORD ITEMS!

# -------------------

# result_dict is the namespace for the interpreter

# TODO: find on an empty tag will lead to a result. NavigableString objects are picked up from templates. So you must check for that with if tag:

# <jump> tags: jump only via its own tag.Tag only jumps on URL that has been recorded in result_dict

# conditions built from result_dict namespace values  and system paramters such as i
# <if> tag acts on such a condition, as does <for> tag.
# Practical example of <if> tag is to run path when a certain variable is not present and while loops.

FAIL = -1
PARTIAL = 0
SUCCESS = 1

DEBUG = False

def set_data_type(interp_function):

	def wrapper(text):
		interpreted_text = interp_function(text)

		if isinstance(interpreted_text,str) and interpreted_text.isdigit():
			interpreted_text = int(interpreted_text)

		return interpreted_text

	return wrapper


def make_regex_fun(regex_ob):

	@set_data_type
	def regex_fun(node):
		node_str = get_text(node)
#		print node_str
		m = regex_ob.search(node_str)
		if m is not None:
			return m.group('result').strip()
		else:
			return None

	return regex_fun


def parse_date(text):
	""" Attempts to parse date from text. Returns None on failure.
	"""

	result = dateparser.parse(text.strip())
	if (result is not None) and hasattr(result,'date'):
		return result.date()
	else:
		print("Could not parse %s as date. Returning None."%text)

	return

def parse_date_regex(text):

	date = None
	for i, date_re in enumerate(date_regexes):
		try:
			m = date_re.search(text)
			dstr_found = m.group()
			if dstr_found is None:
				continue
			print('date regex found "%s" for tried expression %d. Original text: "%s"'%(dstr_found, i, text))
			date = parse_date(dstr_found)
			break
		except Exception as e:
			pass

	if date is None:
		print("Problem getting date from %s"%text)
		return "Not Found"

	return date

def get_date(node):

	dstr = get_text(node)

	return parse_date_regex(dstr)


def get_text(node):
	if isinstance(node, (NavigableString , str)):
		result = str(node)
	else:
		result = getattr(node, 'text','')

	if result.isspace():
		return ''

	return result.replace('\n','').strip()


def nop_fun(node):
	return False

vol_regex = re.compile(r'(?P<volword>Volume|VOL\.*) (?P<result>\d{1,4})',re.I)
issue_regex = re.compile(r'(?P<issueword>Number|Issue|No\.(s)*)(\s+)(?P<result>[\d-]{1,5})',re.I)


email_regexes = []
email_regexes.append(re.compile(r"Electronic address: (?P<email>[^@\s]+@[^@\s]+\.[^@\s]+)",flags = re.I))
email_regexes.append(re.compile(r"Email address([:]*) (?P<email>[^@\s]+@[^@\s]+\.[^@\s]+)",flags = re.I))
email_regexes.append(re.compile(r"Email: (?P<email>[^@\s]+@[^@\s]+\.[^@\s]+)",flags = re.I))
email_regexes.append(re.compile(r"and (?P<email>[^@\s]+@[^@\s]+\.[^@\s]+)",flags = re.I))
email_regexes.append(re.compile(r"(?P<email>[^@\s]+@[^@\s]+\.[^@\s]+)",flags = re.I))
re_HTTP = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
re_phone = re.compile(r"Tel: \+*[\d\-\.\s]+", flags = re.I)
re_alphanumeric = re.compile(r"\w+", flags = re.UNICODE)
re_spaces = re.compile(r"\s+")


# Recall that \S is any non-whitespace chars
DOI = re.compile('(?P<result>10(\.(?P<registrant>(\d|\.)+))(.(\d)+)*\/([\w\S])+)')
chare = re.compile(r'\n')
quotations = re.compile("^\'(?P<result>[\w\s]+)\'$"  )

get_volume = make_regex_fun(vol_regex)
get_issue = make_regex_fun(issue_regex)
get_doi = make_regex_fun(DOI)
get_from_quotes = make_regex_fun(quotations)

command_table = {'text' : get_text, 'date' : get_date, 'volume' : get_volume, 'issue' : get_issue, 'doi': get_doi}


def lt_fun(a,b):

	return a < b

def gt_fun(a,b):

	return a > b

def eq_fun(a,b):

	return a == b





def interpret_attrs(attrs):
	for key, value in attrs.items():
		if not isinstance(value,list):
			value = [value]
		for e in value:
#			print(e)
			if isinstance(e, str) and e.startswith('re('):
				print("Compiling regex: %s"%e)
				#arg = e.split(' ')[1]
				arg = e.strip('re()')
				attrs[key] = re.compile(arg)

condition_funs = {'<': lt_fun, '>' : gt_fun, '=' : eq_fun}

def find_condition(while_arg_str, condition_funs):

	for key in condition_funs:
		if key in while_arg_str:
			return key

	return ''

def find_data_types(a, b):
	"""

	Returns values interpreted in the right datatypes

	example: find_data_types( sub_dict[L[0]] , parse_date(L[1]) )
	"""

	if isinstance(a,datetime.date):

		b = parse_date(b)
		if b is None:
			print("Syntax error: could not parse date %s. Returning None."%b)
	elif isinstance(a,int):
		if b.isdigit():
			b = int(b)

	return b



# --------------------------


def remove_empty_lists(result_list):
#	if not isinstance(result_list, list):
#		result_list = [result_list]

	result_list_copy = []
	for D in result_list:
		if isinstance(D, dict) and ('items' in D.keys()):
			if len(D['items']) == 0:
				pass
			else:
				D['items'] = remove_empty_lists(D['items'])
				result_list_copy.append(D)

		else:
			result_list_copy.append(D)

	return result_list_copy

def rearrange(dict_origin, new_dict = None):
	""" Introduce hierarchy based on tag directives and clean up dict.

		Responds to group tag
	"""

	if new_dict is None:
		new_dict = {}

	for key, value in dict_origin.items():
		if isinstance(value, list):

			new_dict['items'] = []
			accum_list = new_dict['items']
			for list_el in value:
				if isinstance(list_el, dict):
					if len(list_el) == 0:
						continue
					if 'group' in list_el:
						new_list_el = {}
						del list_el['group']
						new_list_el.update(list_el)
						new_list_el['items'] = []
						new_dict['items'].append(new_list_el)
						accum_list = new_list_el['items']
					else:
						accum_list.append(rearrange(list_el))
		else:
			new_dict[key] = value

	return new_dict

def parse_archive_urls(soup_template):

	if isinstance(soup_template, str):
		soup_template = BeautifulSoup(open(soup_template), "html.parser")

	node = soup_template.find('a', attrs = {'class' : 'archive_location'})
	href = node.attrs.get('href','').strip()
	j_protected = node.attrs.get('javascript_protected','').strip()
	if j_protected:
		print ("javascript_protected: %s"%j_protected)

	text_pieces = [e.strip() for e in node.text.split(',')]

	L = []
	for meta_url in [e.strip() for e in href.split(',') ]:
		if '{0}' in meta_url:
			L += [meta_url.format(e) for e in text_pieces]
		else:
			L += [meta_url,]

	return L, j_protected



def open_soup_file(fname):

	with open(fname) as f:
		text = f.read()
		soup = BeautifulSoup(text,'lxml')
	return soup


#class NodeParser():
#	def __init__(self, )

def get_tag_attrs(node):
	renamed_tags = {'ibody' : 'body', 'ihtml' : 'html','ihead' : 'head','any': None}
	if (type(node) == NavigableString) or (isinstance(node, Comment)):
		return '',{}

	name = getattr(node, 'name', '')
	attrs = getattr(node, 'attrs',{})

	# BeautifulSoup doesn't allow body to appear twice in HTML: need to rename second body tag (to ibody)
	name = renamed_tags.get(name, name)

	return name, attrs






def intersection(L1, L2):

#	L = list( set(common_attrs['class']) & set(attrs['class'])  )
#	common_attrs['class'] = [e for e in L if e]

	pass

def is_node(node, name, attrs):
	"""

	Args:
		node: (soup node) live node
		name: (soup node) name of template node
		attrs: (dict) attrs of template node (excl. keywords)

	Used from is_valid_pair method: is_node(self.node_live, name, attrs)
	"""

	if node is None or ((type(node) == NavigableString) or isinstance(node, Comment) ):
		return False

	# get attrs from the live node
	node_attrs = getattr(node,'attrs',{})

	# sub collection of node_attrs where keys are in template attrs
	common_attrs = {key : node_attrs.get(key,'') for key in attrs.keys() }

	# class attr is a list. common_attrs['class'] should be subset of class list of live node
	# this is because live nodes may belong to several classes, whereas the template node to only one of them.
	if 'class' in common_attrs:
		L = list( set(common_attrs['class']) & set(attrs['class'])  )
		common_attrs['class'] = [e for e in L if e]

#	print("common_attrs: %s attrs: %s"%( common_attrs , attrs) )

	return (getattr(node,'name','') == name) and (common_attrs == attrs)


def parse_one_function(cmd_args, node_live, stdin = None):

	if cmd_args.startswith('regex'):
		L2 = cmd_args.split(' ',1)

		if len(L2) > 1:
			regex_str = L2[1].strip()
			if stdin is None:
				stdin = get_text(node_live)
			m = re.search(regex_str, stdin)
			if m is not None:
				return m.group(1).strip()
			else:
				print('regex "%s" not found for %s on "%s"'%(regex_str, L2[0], stdin)  )
				return

	elif cmd_args in command_table:
		if stdin is not None:
			node_live = stdin

		arg_text = command_table.get(cmd_args, nop_fun)(node_live)
		if (arg_text is not None) and arg_text:
			return arg_text
	else:
		# look in actual live attributes
		result = node_live.get(cmd_args)
		if result is not None:
			return result

def parse_functions(cmd_args, node_live):

	pipe = [e.strip() for e in cmd_args.split('|')]
	result = None
	for cmd in pipe:
		result = parse_one_function(cmd, node_live=node_live, stdin=result)
	return result

def record_one(cmd_args, node_live, result_dict, record_key = ''):
	""" parse record attr and run command

	Examples:
		<a record = "href as URL">
	"""

	# maybe change this to a default value
	record_key = cmd_args

	update_dict = {}

	L = cmd_args.strip().split(' as ')
	if len(L) > 2:
		print('Error parsing record attr: keyword "as" appears more than once in "%s"'%cmd_args)
	if len(L) > 1:
		record_key = L[1].strip()

	cmd_args = L[0].strip()

	result = parse_functions(cmd_args, node_live)
	if result is not None:
		update_dict[record_key] = result

	return {"record" : update_dict}


def record(cmd_args, node_live, result_dict, record_key = ''):

	update_dict = {}
	L = cmd_args.strip().split(';')
	for e in L:
		record_dict = record_one(e, node_live, result_dict, record_key)
		update_dict.update(record_dict["record"])

	return {"record" : update_dict}


def condition_fun_one(cmd_args, node_live, result_dict):
	""" Conditionals in templates, interpret one single statement.

	Compares two values, usually one found in template and one in live page.

	TODO: data type for numerical currently determined from var_value (as found in result_dict). This goes wrong if var_value type bad.

	TODO: split on ';' before applying logic, to allow multiple conditions, e.g. "i<5;i>0"
	"""

	condition_str = cmd_args.strip()

	if condition_str:
		L = condition_str.split(' ')
		var_name = L[0]

		if var_name not in result_dict:
			print('Condition variable "%s" not in namespace, returning True'%var_name)
			if DEBUG:
				print("Warning: condition var '%s' not found, returning True. \n result_dict: %s"%(var_name, str(result_dict)))
			return True
		else:
			var_value = result_dict[var_name]

		if len(L) == 1:
			print("Condition string not split, returning True")
			return True

		elif len(L) > 2:
			numerical = find_data_types(var_value, L[2].strip() )
#			print("VALUES: %s vs %s vs %s"%(var_value, numerical, L[2].strip()))

			if numerical is None:
				print("Data type conversion failed for %s. Conditional set to False."%var_value)
				return False
#			print(numerical)
			op = L[1].strip()
			if op not in condition_funs:
				print("Syntax error in condition %s: operation not found. Conditional set to False."%condition_str)
				return False

			cond_fun = condition_funs.get(op,nop_fun)
			return cond_fun(var_value, numerical)   # condition fun executed here!

	return False

def condition_fun(cmd_args, node_live, result_dict):

	L = cmd_args.strip().split(';')

	result = True
	for e in L:
#		print(e, condition_fun_one(e, node_live, result_dict))
		result = result and condition_fun_one(e, node_live, result_dict)

	return result


def extract_resdict_fun(cmd_args, node_live, result_dict):

	return result_dict.get(cmd_args,'')

def extract_attr_fun(cmd_args, node_live, result_dict):

	return cmd_args


def cleanup_counters(result):
	counter_names = ['i' , 'l']

	for e in result:
		for cname in counter_names:
			if cname in e:
				del e[cname]


class NodeParser():

	attrs_keywords_functions = {'record' : record, 'items' : extract_attr_fun, 'on' : extract_resdict_fun, 'javascript_protected' : extract_attr_fun, 'condition' : condition_fun, 'order' : extract_attr_fun}

	def __init__(self, node_template , node_live,live_url, result_dict = None, try_funs = None ):
		""" Calls parse_attr_keywords and stores results, which enter result_dict later.
		"""

		if result_dict is None:
			result_dict = {}

		if callable(try_funs):
			try_funs = [ try_funs, ]

		self.node_template = node_template
		self.node_live = node_live
		self.result_dict = result_dict
		self.live_url = live_url
		self.try_funs = try_funs

		if self.is_valid_pair():
			self.attrs_keywords_result = self.parse_attr_keywords()
		else:
			self.attrs_keywords_result = {}
#		print(self.attrs_keywords_result)

	def parse_attr_keywords(self, result_dict = None):
		""" Parse and interpret the keywords encoded in tag attributes.

		Example keywords: "on", "items", "record".

		Result of executing the statements are stored in result dictionary

		Returns:
			dictionary containing result
		"""

		if not result_dict:
			result_dict = self.result_dict

		attrs_keywords_result = {}
		tag, attrs, attrs_keywords = self.get_tag_attrs(self.node_template)

		for cmd_key, cmd_args in attrs_keywords.items():
			attrs_keywords_result[cmd_key] =  self.attrs_keywords_functions[cmd_key](cmd_args, self.node_live, result_dict)

		return attrs_keywords_result

	def get_tag_attrs(self, node_template = None):
		""" Obtain tag name, dict of all non-keyword tag attributes and dict of keyword tag attributes.
		"""

		if node_template is None:
			node_template = self.node_template
		name, attrs = get_tag_attrs(node_template)
		interpret_attrs(attrs)
		attrs_keywords = {key : attrs[key] for key in attrs if key in self.attrs_keywords_functions.keys()}
		attrs = {key : attrs[key] for key in attrs if key not in self.attrs_keywords_functions.keys()}

		return name, attrs, attrs_keywords

	def is_valid_pair(self):
		""" Are template node and live node in sync?

		Template hopping and running are conditional upon this.
		"""

		if isinstance(self.node_template, (NavigableString, Comment)) or isinstance(self.node_live, (NavigableString, Comment)):
			return False

		name, attrs, attrs_keywords = self.get_tag_attrs()
#		print("Valid pair: %s , name: %s, attrs: %s, live: %s , live_attrs: %s"%(str(is_node(self.node_live, name, attrs)) , name, attrs, getattr(self.node_live, 'name') , getattr(self.node_live, 'attrs')  ))
		return is_node(self.node_live, name, attrs)


	def hop_template(self):
		""" Hops to each template child, and hops on the live children.

		Executed only for valid pairs.

		A hop is done by instantiating a new NodeParser derived object, with class based on the tag name, and calling hop_live_child on it.

		Tree execution ends when every template leaf node has been reached.
		"""

		if not self.is_valid_pair():
			return FAIL # signals failure of this chain

		elif not hasattr(self.node_template, 'children'):
			return SUCCESS # signals success through the chain

		else:
			for child_template in self.node_template.children:
				tag, attrs, attrs_keywords = self.get_tag_attrs(child_template)
				if tag:
					# construct parser object dependent on child node name
					parser_class = parse_table.get(tag, NodeParser)
					np = parser_class(child_template, self.node_live, self.live_url, result_dict = self.result_dict)
					np.hop_live_child()
			return PARTIAL # signals success so far in this chain



	def run(self):
		""" Update result_dict based on stored results from the parse_attr_keywords method call made in __init___
 		"""

		if self.is_valid_pair():

			for key, value in self.attrs_keywords_result.items():
				if isinstance(value, dict):
					update_dict = value.get("record", {})

					self.result_dict.update(update_dict)
#					print(self.result_dict)

#			tag, attrs, attrs_keywords = self.get_tag_attrs(self.node_template)
#			for cmd_key, cmd_args in attrs_keywords.items():
#				self.attrs_keywords_functions[cmd_key](cmd_args, self.node_live, self.result_dict)

	def template_nodes(self):
		""" Provide template nodes, based on current template node, to be used in hop_live_child

		This function can be modified for instance to provide a child instead of the current template node in derived classes.
		"""
		if not isinstance(self.node_template, (NavigableString,Comment)):
			return [self.node_template]

		return []

	def live_nodes(self):
		""" Provide live nodes for hop_live_child, where new parsers are made based on result from self.live_nodes() and self.template_nodes()
		"""
		tag, attrs, attrs_keywords = self.get_tag_attrs(self.node_template)

		if tag: # IMPORTANT. Make this separate function. templ2children
#			print("yo: %s and %s"%(self.__class__,type(self.node_live)))

			if self.node_live is None:
				print('Warning! live_node is None. Check for "Lib failed" message above for all scraping modules.')
				return []
			if not isinstance(self.node_live, (NavigableString, Comment)):
				next_node_live = self.node_live.find(tag, attrs = attrs)
				if next_node_live is not None:
					return [next_node_live]

		return []

	def get_templ_attr(self, attr_name = 'items'):
		""" Obtain an attr from templ tag

		Example: <for condition = 'i lt 5' items = 'my_items'>
		"""

		attrs = getattr(self.node_template, 'attrs')
		return attrs.get(attr_name,'items')


	def act_on_next_parser(self, parser):
		""" Called on next parser from this parser immediately after its creation.
		"""
		parser.run()

	def hop_live_child(self):
		""" hop to first live child matching template tag.

		Also runs the template node on the child tag.
		"""

		# WHY DO WE NEED TO INCLUDE i in child_result here to avoid i not found warning in first iteration of FOR Command tag?

		result = []
		for next_node_live in self.live_nodes():
			# probe with the children on the list of live nodes (order important)
			for template_node in self.template_nodes():

				child_result = {'i' : len(result)}
				len_start = len(child_result)
				tag = getattr(template_node, 'name', '')
				parser_class = parse_table.get(tag, NodeParser)
				np = parser_class(template_node, next_node_live, self.live_url, result_dict = child_result)
				self.act_on_next_parser(np)
				status = np.hop_template() # can use status later

				if len(child_result)>len_start:
					result.append(child_result)

		cleanup_counters(result)

		for D in result:
			self.result_dict.update(D)



class CommandParser(NodeParser):
	""" Base class for command nodes. Yields template_nodes that are children of the command tag.
	"""

	def act_on_next_parser(self, parser):
		parser.hop_live_child()
		parser.run()


	def live_nodes(self):
		return [self.node_live]

	def run(self):

		print("Error: running command tag '%s' on a live node '%s'. Directly nesting command nodes may cause this problem."%(self.__class__, getattr(self.node_live,'name','') ))
		return


	def is_valid_pair(self):
		""" Are template node and live node in sync?

		Template hopping and running are conditional upon this.
		"""

#		if isinstance(self.node_live, (NavigableString, Comment)):
#			return False

		if isinstance(self.node_template, (NavigableString, Comment)) or isinstance(self.node_live, (NavigableString, Comment)):
			return False

		return True

	def template_nodes(self):
		""" Provide template nodes, based on current template node, to be used in hop_live_child

		Command tags are artificial DOM elements in the template, and must be skipped when matching live DOM elements.
		"""

		if self.is_valid_pair():
			if hasattr(self.node_template, 'children'):
				return [e for e in self.node_template.children if not isinstance(e,(NavigableString, Comment))]

		return []

class IfParser(CommandParser):
	""" The validity of this tag dependends only on the conditional in the tag
	"""


	def is_valid_pair(self):
		""" Are template node and live node in sync?

		Template hopping and running are conditional upon this.
		"""

#		if isinstance(self.node_live, (NavigableString, Comment)):
#			return False

		if isinstance(self.node_template, (NavigableString, Comment)) or isinstance(self.node_live, (NavigableString, Comment)):
			return False

		# Its i only here that the condition key is used. Condition result has been determined earlier and stored.

		# self.attrs_keywords_result doesn't exist yet, and will be
		attrs_keywords_result = self.parse_attr_keywords()

		return attrs_keywords_result.get('condition', False)



class JumpParser(CommandParser):

	def live_nodes(self):
		"""
		Example:
		      <jump on = "details_url"></jump>
		"""

#		tag, attrs, attrs_keywords = self.get_tag_attrs(self.node_template)

		# HOW TO IMPLEMENT javascript_protected IN JUMP TAG?

		javascript_protected = self.attrs_keywords_result.get('javascript_protected', False)

		if javascript_protected == 'true':
			javascript_protected = True


		link_url = self.attrs_keywords_result.get('on', '')
		if link_url:
			link_url = urljoin(self.live_url, link_url)

			try:
#
				if DEBUG or self.try_funs is None:
					nested_soup = open_soup_file(link_url)
				else:
					nested_soup = url2soup(link_url, try_funs = self.try_funs, javascript_protected = javascript_protected)

				if nested_soup is None:
					print("JumpParser Warning! Soup failed, no jump to %s"%link_url)
				else:
					print("Jumping to %s"%link_url)


				return [nested_soup]

			except Exception as e:
				print("Couldn't open '%s' \n %s"%(link_url, e))

		return []


class StringParser(NodeParser):

	def is_valid_pair(self):
		""" Are template node and live node in sync?

		Template hopping and running are conditional upon this.
		"""

		if isinstance(self.node_template, (NavigableString, Comment)):
			return False

		name, attrs, attrs_keywords = self.get_tag_attrs()
		return isinstance(self.node_live, NavigableString) and (name == 'str')



class ForParser(CommandParser):



	def act_on_next_parser(self, parser):

		parser.run()


	def live_nodes(self):
		""" For tag live_nodes method finds all node_live decendants with name tag matching one of the children of the for tag in the template.
		"""

		names_and_attrs = []
		for child_template in self.template_nodes():
			tag, attrs, attrs_keywords = self.get_tag_attrs(child_template)
			if tag:
				names_and_attrs.append((tag, attrs, child_template))

		# child tag names in template
		total_tags = [e[0] for e in names_and_attrs]

		# perform find on multiple tags at once
		live_children = self.node_live.find_all(name=total_tags)

		order = self.attrs_keywords_result.get('order','')
		if order.lower() == 'reversed':
			live_children.reverse()

		return live_children

	def scan_nodes(self):
		""" Try each template node in the current hop on each live node and look for valid pairs.

		Loop counters are inserted into child result dicts

		Loop counters:
			i : the current length of the result list
			l : the loop counter, increased by 1 inside the deepest node loop level

		Template examples
			<if condition = "l = 2"></if> will pick the second element in a list of live nodes if there's only one template node. This doesn't work with counter i, as this counts the length of the current result list.

		"""

		loop_counter = 0
		result = []
		for next_node_live in self.live_nodes():
			# probe with the children on the list of live nodes (order important)
			for template_node in self.template_nodes():

				if DEBUG:
					print("Loop counter: %d"%loop_counter)
				loop_counter += 1

				# This needs to be changed to a more appropriate counter
				child_result = {'i': len(result) , 'l' : loop_counter }
				len_start = len(child_result)

				tag = getattr(template_node, 'name', '')
				parser_class = parse_table.get(tag, NodeParser)
				np = parser_class(template_node, next_node_live, self.live_url, result_dict = child_result)
				self.act_on_next_parser(np)
				status = np.hop_template() # can use status later

				attrs_keywords_result = self.parse_attr_keywords(result_dict = child_result)
				if 'condition' in attrs_keywords_result:
#					print(attrs_keywords_result.get('condition'))
					if not attrs_keywords_result['condition']:
						# stop looping when condition tag yields False
						if DEBUG:
							print("Loop ends: condition False encountered.")
						return result
					else:
						if DEBUG:
							print('Warning: no "condition" found in loop. ')


				# does child_result have anything apart from counter i?
				if len(child_result) > len_start:
					result.append(child_result)

		return result


	def hop_live_child(self):
		""" hop to first live child matching template tag.

		Also runs the template node on the child tag.
		"""

		result = self.scan_nodes()

		cleanup_counters(result)

#		print(result)
#		if len(result) > 1:
#			items_name = self.attrs_keywords_result.get('items','items')
#			self.result_dict[items_name] = result
#		elif len(result) == 1:
#			self.result_dict.update(result[0])

		items_name = self.attrs_keywords_result.get('items','items')
		self.result_dict[items_name] = result


class ForChildParser(ForParser):
	""" Finds live match to first template node (child of this command tag), and loops over its sibblings, probing with all template nodes (the children of this for node).

	This template tag must be inside a template tag that matches a live tag that closely encloses these sibblings.

	This loop will collect NavigableString nodes also.

	This loop is suitable for cases where sequences of adjacent live tags are repeated, while there is no repeating enclosing parent tag, and can be used as a general loop also.

	"""


	def live_nodes(self):
		""" Finds live match to first template node (child of this command tag), and yields its sibblings.
		"""

		template_nodes = self.template_nodes()
		if template_nodes:
			start_node_template = template_nodes[0]
			result = []
			tag, attrs, attrs_keywords = self.get_tag_attrs(start_node_template)

#			print(tag, attrs, attrs_keywords)
			# INSERT REGEX CODE HERE AND IN LIVE_NODES METHOD OF OTHER CLASSES

			if tag:
				child_node_live = self.node_live.find(tag, attrs = attrs)
#				print(child_node_live)
				if child_node_live is None:
					print("Warning: no child_node_live for %s with %s"%(tag , attrs))
					return []
				else:
					live_children = [e for e in child_node_live.parent.contents if not isinstance(e, Comment)]

		order = self.attrs_keywords_result.get('order','')
		if order.lower() == 'reversed':
			live_children.reverse()

		return live_children

parse_table = {'forchild' : ForChildParser,'for' : ForParser, 'str' : StringParser, 'jump' : JumpParser, 'if' : IfParser, 'command' : CommandParser}

def example():

	live_url = 'test_page.html'
	template_url = 'test_template.html'

	if len(sys.argv) > 1:
		template_url = sys.argv[1]

		if len(sys.argv) > 2:
			live_url = sys.argv[2]

	print('Scraping "%s" using template "%s"'%(live_url, template_url))

	soup_template = open_soup_file(template_url)
	soup = open_soup_file(live_url)

	np = NodeParser(soup_template, soup, live_url)
	np.hop_template()
	print (json.dumps(np.result_dict, indent = 2, default = str))

if __name__ == "__main__":

	example()
