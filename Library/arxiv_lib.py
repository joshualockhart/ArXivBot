from customised_exceptions import NoArgumentError, GetRequestError, UnknownError, NoCategoryError
import requests
import feedparser
import sys, os
import cgi
import today_lib as tl

# MODULE-SCOPE VARIABLE

ALL_CATEGORIES = ['stat.AP', 'stat.CO', 'stat.ML', 'stat.ME', 'stat.TH', 'q-bio.BM', 'q-bio.CB', 'q-bio.GN', 'q-bio.MN', 'q-bio.NC', 'q-bio.OT',
				  'q-bio.PE', 'q-bio.QM', 'q-bio.SC', 'q-bio.TO', 'cs.AR', 'cs.AI', 'cs.CL', 'cs.CC', 'cs.CE', 'cs.CG', 'cs.GT', 'cs.CV', 'cs.CY',
				  'cs.CR', 'cs.DS', 'cs.DB', 'cs.DL', 'cs.DM', 'cs.DC', 'cs.GL', 'cs.GR', 'cs.HC', 'cs.IR', 'cs.IT', 'cs.LG', 'cs.LO', 'cs.MS',
				  'cs.MA', 'cs.MM', 'cs.NI', 'cs.NE', 'cs.NA', 'cs.OS', 'cs.OH', 'cs.PF', 'cs.PL', 'cs.RO', 'cs.SE', 'cs.SD', 'cs.SC', 'nlin.AO',
				  'nlin.CG', 'nlin.CD', 'nlin.SI', 'nlin.PS', 'math.AG', 'math.AT', 'math.AP', 'math.CT', 'math.CA', 'math.CO', 'math.AC', 'math.CV',
				  'math.DG', 'math.DS', 'math.FA', 'math.GM', 'math.GN', 'math.GT', 'math.GR', 'math.HO', 'math.IT', 'math.KT', 'math.LO', 'math.MP',
				  'math.MG', 'math.NT', 'math.NA', 'math.OA', 'math.OC', 'math.PR', 'math.QA', 'math.RT', 'math.RA', 'math.SP', 'math.ST', 'math.SG',
				  'astro-ph', 'cond-mat.dis-nn', 'cond-mat.mes-hall', 'cond-mat.mtrl-sci', 'cond-mat.other', 'cond-mat.soft', 'cond-mat.stat-mech',
				  'cond-mat.str-el', 'cond-mat.supr-con', 'gr-qc', 'hep-ex', 'hep-lat', 'hep-ph', 'hep-th', 'math-ph', 'nucl-ex', 'nucl-th',
				  'physics.acc-ph', 'physics.ao-ph', 'physics.atom-ph', 'physics.atm-clus', 'physics.bio-ph', 'physics.chem-ph', 'physics.class-ph',
				  'physics.comp-ph', 'physics.data-an', 'physics.flu-dyn', 'physics.gen-ph', 'physics.geo-ph', 'physics.hist-ph', 'physics.ins-det',
				  'physics.med-ph', 'physics.optics', 'physics.ed-ph', 'physics.soc-ph', 'physics.plasm-ph', 'physics.pop-ph', 'physics.space-ph', 'quant-ph']

# MODULE METHODS

# This method returns the number of available arXiv categories.

def number_categories():

	return len( ALL_CATEGORIES )

# This method takes an integer i and returns the i-th category in the list ALL_CATEGORY.

def single_category(category_index):

	if not isinstance(category_index, int):
		raise TypeError('The index is not an integer.')

	if category_index < len( ALL_CATEGORIES ) and category_index >= 0:
		return ALL_CATEGORIES[category_index]
	else:
		raise IndexError('The module-scope list ALL_CATEGORY has no element ' + str(category_index) + '.')

# Review response, it will review the dictionary obtained from parse_response
# and pass the following information for each entries:
#
# - title
# - authors
# - year
# - link
#
# Only these information are passed since they will go to the Telegram Bot.
# The return argument is a list of dictionary with these entries.

def review_response(dictionary, max_number_authors):

	results_list = []

	if not isinstance(max_number_authors, int):
		raise TypeError('The number of authors has to be an integer.')

	if max_number_authors < 1:
		raise ValueError('The maximum number of authors has to be bigger than 1.')

	if not isinstance(dictionary, dict):
		raise TypeError('The argument passed is not a dictionary.')

	try:
		if not isinstance(dictionary['entries'], list):
			raise TypeError('The field entries is corrupted.')
	except KeyError:
		raise NoArgumentError('No entries have been found during the search.')

	for entry in dictionary['entries']:

		if not isinstance(entry, dict):
			raise TypeError('One of the entries is corrupted.')

		# Only write the important data in the dictionary
		element = {'title' : one_line_title(entry),
				   'authors' : compact_authors(entry, max_number_authors),
				   'year' : find_year(entry),
				   'link' : is_field_there(entry, 'link')}
		
		# Check whether all field in the element are None
		is_empty = element['title'] == None and element['authors'] == None and element['year'] == None and element['link'] == None

		if not is_empty:
			results_list.append(element)

	if len(results_list) == 0:
		raise NoArgumentError('No entries have been found during the search.')
	
	return results_list

# This function returns the total number of results of the search.

def total_number_results(dictionary):

	if not isinstance(dictionary, dict):
		raise TypeError('The argument passed is not a dictionary.')

	feed_information = is_field_there(dictionary, 'feed')

	if feed_information == None:
		raise NoArgumentError('No feed have been returned by the search.')

	if not isinstance(feed_information, dict):
		raise TypeError('The field feed is corrupted.')

	total_results = is_field_there(feed_information, 'opensearch_totalresults')

	if total_results == None:
		raise NoArgumentError('The feed got corrupted.')

	return int(total_results)

# This function is needed for the review_response.
# It checks that the dictionary has something associated to the key, and if not, it returns None.

def is_field_there(dictionary, key):

	try:
		return dictionary[key]
	except:
		return None

# This function is needed for the review_response.
# It removes the newline symbols \n from the title.
# It also escape the HTML symbols <, >, &, so that they are correctly interpreted by telepot.send_message().

def one_line_title(dictionary):

	title = is_field_there(dictionary, 'title')

	if isinstance(title, unicode):
		title = title.replace(u'\n',u'')
		title = title.replace(u'  ',u' ')
		title = cgi.escape(title)
		return title
	else:
		return None

# This function is needed for the review_response.
# It unifies the name of the authors in a single one, and return a Unicode string (if there are some authors).
# It also cuts the number of authors after max_number_authors, and replaces the remaining with 'et al.'

def compact_authors(dictionary, max_number_authors):

	authors_list = is_field_there(dictionary, 'authors')
	authors_string = unicode( '' , "utf-8")
	authors_number = 1

	if isinstance(authors_list, list):
		for author in authors_list:
			author_name = is_field_there(author, 'name')
			if authors_number > max_number_authors:
				authors_string = authors_string + u'et al.**'
				break
			if isinstance(author_name, unicode) and authors_number <= max_number_authors:
				authors_number +=1
				authors_string = authors_string + author_name + unicode( ', ' , "utf-8")

	else:
		return None

	# Check if we have something in the authors string
	if len(authors_string) == 0:
		return None
	else:
		authors_string = authors_string[: -2]
		return authors_string

# This function is needed for the review_response.
# For a given date, it returns the year.

def find_year(dictionary):

	date = is_field_there(dictionary, 'date')

	if isinstance(date, unicode) and len(date) > 3:
		date = date[0:4]
		return date
	else:
		return None

# Parse the response. It modifies the response obtained by the request library
# making it a raw data (string). Then, it parse it using FeedParser.
# It returns a dictionary.

def parse_response(response):
	
	if not isinstance(response, requests.models.Response):
		raise TypeError('The argument passed is not a Response object.')

	rawdata = response.text

	parsed_response = feedparser.parse(rawdata)

	return parsed_response

# Request function to communicate with the arXiv and download the informations
# It takes a string (the link) as argument
# Check for the main connection errors.
# Return the response.

def request_to_arxiv(arxiv_search_link):

	if not ( isinstance(arxiv_search_link, unicode) or isinstance(arxiv_search_link, str) ):
		raise TypeError('The argument passed is not a string.')

	# Making a query to the arXiv
	try:
		response = requests.get( arxiv_search_link ) 
	except requests.exceptions.InvalidSchema as invalid_schema:
		raise invalid_schema
	except requests.exceptions.MissingSchema as missing_schema:
		raise missing_schema
	except:
		raise GetRequestError('Get from arXiv failed. Might be connection problem')

	# Check the status of the response
	try:
		response.raise_for_status()
	except requests.exceptions.HTTPError as connection_error:
		raise connection_error
	else:
		return response

# The function adds to the arXiv link an extra field, which specifies
# the number of results we want to obtain. It output the link with
# at the end the new specification.

def specify_number_of_results(arxiv_search_link, number_of_results):

	if number_of_results < 0:
		raise ValueError('The number of results you are interested in cannot be negative.')

	arxiv_search_link += '&max_results=' + str(number_of_results)

	return arxiv_search_link

# The function provides the correct time range for checking daily submissions.
# The input is a GMT time step, and the output depends on the rules about
# submission of the arXiv (see https://arxiv.org/help/submit#availability).
# The output is a string which can be added to the request link to arXiv for
# checking the new submissions.

def time_range_for_today_search(time_information):

	current_weekday = tl.which_weekday(time_information)
	submission_range = 'submittedDate:['
	deadline_submission = '1800'

	if current_weekday == 'Mon':
		initial_date = tl.move_current_date(-4, time_information)
		final_date = tl.move_current_date(-3, time_information)
	elif current_weekday == 'Tue':
		initial_date = tl.move_current_date(-4, time_information)
		final_date = tl.move_current_date(-1, time_information)		
	elif current_weekday == 'Wed' or current_weekday == 'Thu' or current_weekday == 'Fri':
		initial_date = tl.move_current_date(-2, time_information)
		final_date = tl.move_current_date(-1, time_information)
	elif current_weekday == 'Sat':
		initial_date = tl.move_current_date(-3, time_information)
		final_date = tl.move_current_date(-2, time_information)
	elif current_weekday == 'Sun':
		initial_date = tl.move_current_date(-4, time_information)
		final_date = tl.move_current_date(-3, time_information)

	submission_range += initial_date + deadline_submission + '+TO+' + final_date + deadline_submission + ']'

	return submission_range

# This function search the submissions which were available to the users on the date
# specified by the time_information, in a given category (e.g., quant-ph) specified by
# subject_category. The function returns the arXiv link for the search.

def search_day_submissions(time_information, subject_category, arxiv_search_link):

	if not category_exists(subject_category):
		raise NoCategoryError('The passed category is not in the ArXiv')

	time_range = time_range_for_today_search(time_information)
	arxiv_search_link += 'cat:' + subject_category + '+AND+' + time_range

	return arxiv_search_link

# This function checks whether the subject_category is an existing category of the arXiv,
# and returns a boolean accordingly.

def category_exists(subject_category):

	return subject_category in ALL_CATEGORIES

# Advanced search the arXiv.
#
# As parameter, it takes the following parameters:
#
# au			Author
# ti			Title
# abs			Abstract
# co			Comment
# jr			Journal Reference
# cat			Subject Category
# rn			Report Number
# id			Id
# arxiv_search_link	The arXiv link where making the query
# 
# And it make the link for the request to arXiv, which will be passed
# to the request_to_arxiv method.
# 
# If a variable is not a string, it is not included in the function,
# But no exception is raised. Exception is raised only is the search
# is empty. After the query is done, the response is returned.

def advanced_search(author, title, abstract, comment, jref, category, rnum, identity, arxiv_search_link):

	# Initialising constant values for the search
	connector = '+AND+'
	length_check = len(arxiv_search_link)

	# Creating the dictionary for the search
	parameters = {
	 'au:' : author ,
	 'ti:' : title ,
	 'abs:' : abstract ,
	 'co:' : comment ,
	 'jr:' : jref ,
	 'cat:' : category ,
	 'rm:' : rnum ,
	 'id:' : identity
	 }

	# Creating the search string, adding each term iff it is a string
	for key in parameters:
		if isinstance(parameters[key], str):
			arxiv_search_link += key + parameters[key] + connector

	# Check that search_def is not empty. In that case, return error
	if len(arxiv_search_link) == length_check:
		raise NoArgumentError('No arguments have been provided to the search.')

	# Remove last connector fromt the search
	arxiv_search_link = arxiv_search_link[: - len(connector) ]

	return arxiv_search_link

# The simple search on the arXiv.
# 
# It takes the argument of the search, which is searched in the all fields,
# such as title, author, etc. The argument of this function has to be a string,
# or a list of strings. If nothing is passed, the search is not performed.
# Returns the link for the call to arXiv

def simple_search(words, arxiv_search_link):

	# Initialising constant values for the search
	connector = '+AND+'
	length_check = len(arxiv_search_link)
	key = 'all:'

	# If the argument is a list of words, iterate over it
	if isinstance(words, list):
		for word in words:
			if isinstance(word, str) or isinstance(word, unicode):
				arxiv_search_link += key + word + connector

	# If it is a single string, add it without iterations
	elif isinstance(words, str) or isinstance(words, unicode):
		arxiv_search_link += key + words + connector

	# Check that search_def is not empty. In that case, return error
	if len(arxiv_search_link) == length_check:
		raise NoArgumentError('No arguments have been provided to the search.')

	# Remove last connector from the search
	arxiv_search_link = arxiv_search_link[: - len(connector) ]

	return arxiv_search_link