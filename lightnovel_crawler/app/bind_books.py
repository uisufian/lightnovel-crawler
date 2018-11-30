#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
To bind into ebooks
"""
import os
import re
from concurrent.futures import ThreadPoolExecutor
from logging import Logger

from bs4 import BeautifulSoup
from PyInquirer import prompt

from ..utils.binding import bind_html_chapter, bind_epub_book, epub_to_mobi
from ..utils.kindlegen_download import download_kindlegen, retrieve_kindlegen

logger = Logger('BIND_BOOKS')


def make_data(app):
    data = {}
    if app.pack_by_volume:
        for vol in app.crawler.volumes:
            data['Volume %d' % vol['id']] = [
                x for x in app.chapters
                if x['volume'] == vol['id']
                and len(x['body']) > 0
            ]
        # end for
    else:
        data[''] = app.chapters
    # end if
    return data
# end def


def make_texts(app, data):
    text_files = []
    for vol in data:
        dir_name = os.path.join(app.output_path, 'web', vol)
        os.makedirs(dir_name, exist_ok=True)
        for chap in data[vol]:
            file_name = '%s.txt' % str(chap['id']).rjust(5, '0')
            file_name = os.path.join(dir_name, file_name)
            with open(file_name, 'w', encoding='utf-8') as file:
                body = chap['body'].replace('</p><p', '</p>\n<p')
                soup = BeautifulSoup(body, 'lxml')
                text = '\n\n'.join(soup.stripped_strings)
                text = re.sub('[\r\n]+', '\r\n\r\n', text)
                file.write(text)
                text_files.append(file_name)
            # end with
        # end for
    # end for
    logger.warn('Created: %d text files', len(text_files))
    return text_files
# end def


def make_htmls(app, data):
    web_files = []
    for vol in data:
        dir_name = os.path.join(app.output_path, 'web', vol)
        os.makedirs(dir_name, exist_ok=True)
        for i in range(len(data[vol])):
            chapter = data[vol][i]
            prev_chapter = data[vol][i - 1] if i > 0 else None
            next_chapter = data[vol][i + 1] if i + 1 < len(data[vol]) else None
            html, file_name = bind_html_chapter(chapter, prev_chapter, next_chapter)

            file_name = os.path.join(dir_name, file_name)
            with open(file_name, 'w', encoding='utf-8') as file:
                file.write(html)
            # end with
            web_files.append(file_name)
        # end for
    # end for
    logger.warn('Created: %d html files', len(web_files))
    return web_files
# end def

def make_epubs(app, data):
    epub_files = []
    for vol in data:
        if len(data[vol]) > 0:
            epub_files.append(bind_epub_book(
                app,
                volume=vol,
                chapters=data[vol],
            ))
        # end if
    # end for
    return epub_files
# end def


def make_mobis(app, epubs):
    kindlegen = retrieve_kindlegen()
    if not kindlegen:
        answer = prompt([
            {
                'type': 'confirm',
                'name': 'fetch',
                'message': 'Kindlegen is required to create *.mobi files. Get it now?',
                'default': True
            },
        ])
        if not answer['fetch']:
            logger.warn('Mobi files were not generated')
            return
        # end if
        download_kindlegen()
        kindlegen = retrieve_kindlegen()
        if not kindlegen:
            logger.error('Mobi files were not generated')
            return
        # end if
    # end if

    mobi_files = []
    for epub in epubs:
        file = epub_to_mobi(kindlegen, epub)
        if file:
            mobi_files.append(file)
        # end if
    # end for
    return mobi_files
# end def


def bind_books(app):
    data = make_data(app)
    make_texts(app, data)
    make_htmls(app, data)
    epubs = make_epubs(app, data)
    make_mobis(app, epubs)
# end def
