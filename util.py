#!/usr/bin/env python3

import re
import datetime
import sys, inspect
import copy



def make_months():
    months = []
    for i in range(1,13):
        months.append( datetime.date(2008, i, 1).strftime('%B'))

    return months

mths = make_months()

date_re_word = re.compile(r'(\d){1,2}(\s)+(%s)(\s)+(\d){1,4}'%'|'.join(mths+[m[:3] for m in mths]) ,re.I)
date_re_word2 = re.compile(r'(%s)(\s)+(\d){1,2},(\s)*(\d){4}'%'|'.join(mths+[m[:3] for m in mths]) ,re.I)
date_re_word3 = re.compile(r'(%s)(\s|,)(\s)*(\d){4}'%'|'.join(mths+[m[:3] for m in mths]) ,re.I)
date_re_numbers = re.compile(r'(\.|/|\\|-)'.join(['\d{1,4}']*3)   )
# date_re_word must occur first!
date_regexes = [date_re_word, date_re_word2, date_re_word3, date_re_numbers]


def is_mod_function(mod, func):
    return inspect.isfunction(func) and inspect.getmodule(func) == mod

def list_functions(mod):
    return [func.__name__ for func in mod.__dict__.itervalues()
            if is_mod_function(mod, func)]


def write(fname,obj):
    f = open(fname,'w')
    json.dump(obj,f)
    f.close()

def read(fname):
    f = open(fname,"r")
    return json.load(f)


def get_neat_text(tag):
    return re.sub(chare, '', tag.text.strip()  )

def simplify_text(tag):
    return re.sub(chare, '', (tag.text.encode('utf-8')).lower()).strip()



def add_times_to_dates(data):
    """ Add time field to dates in data dict to allow mongodb insertion
    """

    if isinstance(data, list):
        for sub_dict in data:
            add_times_to_dates(sub_dict)
        return

    for key, value in data.items():
        if isinstance(value, datetime.date):
            data[key] = datetime.datetime.combine(value, datetime.time.min)



def unwind(data, max_depth = 1000, stop_term = ''):
    """ Unwind nested dictionaries by repeating higher level fields.

        Args:
            max_depth: (int), maximum depth to unwind.
            stop_term: (str), stop unwinding once this term appears as a key in dict.

        Returns:
            Unwound dictionary

    """

    result_list = []

    def unwinder(data, row = None, depth = 0):

        # keep copying
        # first sort values according to whether they are list or not

        if row is None:
            row = {}
        else:
            row = copy.deepcopy(row)

        for key, value in data.items():
            if key != 'items':
                row[key] = data[key]

        if 'items' in data.keys():
            if (depth < max_depth) and (stop_term not in data.keys()):
                for item in data['items']:
                    unwinder(item,row, depth = depth + 1)
            else:
                row['items'] = data['items']
                result_list.append(row)
        else:
            result_list.append(row)

    row = {}
    unwinder(data, row)

    return result_list
