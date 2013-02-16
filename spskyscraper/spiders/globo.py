# -*- coding: utf-8 -*-
#
# If you're reading this. Then this is your soundtrack for the code.
#
# https://soundcloud.com/clownandsunset/sets/acid-pauli-mst
#
from scrapy import log
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.contrib.spiders import CrawlSpider, Rule

from spskyscraper.items import MateriaItem, CommentItem

import re,hashlib,urllib,json

ALLOWED_DOMAINS=['globo.com','g1.globo.com', 'comentarios.globo.com', 'comentarios.globo.com.br' ]
COMMENT_RESUME_URL="http://comentarios.globo.com/comentarios/{materia_section}/{materia_id}/{materia_url}/{materia_shorturl}/{materia_title}/numero"
COMMENT_PAGE_URL="http://comentarios.globo.com/comentarios/{materia_section}/{materia_id}/{materia_url}/{materia_shorturl}/{materia_title}/{page}.json"

class GloboSpider(BaseSpider):
    name = 'globo'
    allowed_domains = ALLOWED_DOMAINS

    def __init__(self,*args,**kwargs):
        super(GloboSpider,self).__init__(*args,**kwargs)

        self.start_urls = [kwargs.get('url')]

    def globo_urlquote( self, data ):
        """ Globo has it's own specific encoding. Weird, i guess """
        return urllib.quote( data.replace('/','@@'), '' )

    def get_comment_page(self,pageNumber=1):
        self.pagination_data['page'] = pageNumber
        d = dict( self.comment_data.items() + self.pagination_data.items() )
        return COMMENT_PAGE_URL.format( **d )

    def parse_single_comment(self, comm_tree):
        n_com = CommentItem()
        n_com['type']       = 'Comment'
        n_com['author']     = comm_tree['Usuario']['nome']
        n_com['author_url'] = comm_tree['facebook_id']
        n_com['comment']    = comm_tree['texto']
        return n_com

    def parse_comment_page_json(self,response):
        page = response.url.split('/')[-1].split('.json')[0]
        rjson = {}
        try:
            data =  re.search('__callback_listacomentarios\(([\s\S\n]*)\)',response.body, re.MULTILINE).groups()[0]

            # Clean it because it's not always a valid json
            rjson =  json.loads( data.replace('\r','\\r').replace("\\'","\\\\'") )

            for c in rjson['itens']:
                yield self.parse_single_comment(c)

        except ValueError as e:
            print "Could not decode page %s " % page


    def parse_comment_resume_json(self, response):
        """
            Que gostava de politica em 1966...
            E hoje dança no frenetic... dancing days. . /. puru pruru!

            Ela me conta que era atriz e trabalhour no "Haiiiir"
            Com alguns homens foi feliz, com outros foi mulher.

            Que tem muito ódio no coração,
            Que tem dado muito amor,
            Espalhado muito prazer e muita dor.
        """
        rjson =  json.loads( re.search('__callbackjsonp_verificaTotalComentarios\(([\s\S\n]*)\)',response.body, re.MULTILINE).groups()[0] )
        self.pagination_data = {'page': 1, 'max': rjson['limitePaginas'], 'len': rjson['numeroDeComentarios'], 'qtd': rjson['itensPorPagina'] }

        # Now we go page after page to fetch the comments
        #for page in xrange(1,self.pagination_data['max']+1):
        for page in xrange(1,10):
            yield Request( self.get_comment_page(page) , callback=self.parse_comment_page_json )

    def parse(self, response):
        """ Parse the materia """
        hxs = HtmlXPathSelector(response)
        m   = MateriaItem()

        m['type'] = 'Materia'

        # Save title/author/url
        m['title']  = hxs.select('//*[@class="entry-title"]/text()').extract()
        m['url']    = response.url
        m['id']     = hashlib.sha1( response.url.split('/')[-1] ).hexdigest().upper()

        log.msg("Parsing %s" % response.url, level=log.INFO)

        # Save the page to a file
        filename = response.url.split("/")[-1]
        #m['page'] = scrapper['mirror'] + filename
        #open( m['page'], 'wb').write(response.body)

        # Save it
        yield m

        # Now fetch the comments. First get the javascript source to build a
        # comment url
        comm_data_re = re.search('comentarios\(([\s\S\n]*?)\);',response.body, re.MULTILINE)
        comm_data_rjson = comm_data_re.groups()[0]

        # Fix markup a little bit to a saner json format
        comm_data_rjson = re.sub('[\n\t    ]','', comm_data_rjson)

        # Put the 'key' between double quotes
        comm_data_rjson = re.sub('([,{])(\w+)\:','\\1"\\2":',comm_data_rjson) \
                            .replace('\'','\"') # Put the 'value' between double quotes

        # Now it's a valid json. Convert to a python dict.
        comm_data = json.loads( comm_data_rjson )
        self.comment_data = {'materia_section': self.globo_urlquote( comm_data['uri'] ) ,
                             'materia_id': comm_data['idExterno'],
                             'materia_url': self.globo_urlquote( comm_data['url']),
                             'materia_shorturl': self.globo_urlquote( comm_data['shortUrl'] ),
                             'materia_title': self.globo_urlquote( comm_data['titulo'] ) }

        # Ok, now we can go to this article comments resume. page
        comment_url = COMMENT_RESUME_URL.format( **self.comment_data )
        yield Request(comment_url, callback=self.parse_comment_resume_json)
