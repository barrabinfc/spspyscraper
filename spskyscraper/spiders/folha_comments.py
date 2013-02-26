# -*- coding: utf-8 -*-
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy import log

from spskyscraper.items import MateriaItem, CommentItem

import re,hashlib

ALLOWED_DOMAINS=['folha.com','folha.uol.com.br','folha.com.br','comentarios.folha.com.br']
COMMENT_URL="http://comentarios.folha.com.br/comentarios/{comment_id}"

class FolhaSpider(BaseSpider):
    name = 'folha_comments'
    allowed_domains = ALLOWED_DOMAINS

    def __init__(self,*args,**kwargs):
        super(FolhaSpider,self).__init__(*args,**kwargs)

        self.start_urls = [kwargs.get('url')]

    def parse_comment_page(self,response):
        hxs = HtmlXPathSelector(response)

        comments = hxs.select("//li[contains(concat(' ',normalize-space(@class),' '),' comment ')]")

        def read_comment(comments):
            json_data = []
            for comm in comments:
                author = comm.select('h6/span/a/text()').extract()
                author_url = comm.select('h6/span/a/@href').extract()
                comment = '\n'.join( comm.select('p/text()').extract()[:-1] )

                comment =  comment.replace('\r','\\r').replace("\\'","'")

                # Recurse into child comments, if necessary
                child_comments = comm.select("ol/li")
                if child_comments:
                    json_data = json_data + read_comment(child_comments)

                n_com = CommentItem()
                n_com['type']       = 'Comment'
                n_com['author']     = author[0].split('(')[0].strip()
                n_com['author_url'] = author_url[0]
                n_com['comment']    = ''.join(comment)

                json_data.append( n_com )

            return json_data

        # Fetch all comments
        comments = hxs.select("//li[contains(concat(' ',normalize-space(@class),' '),' comment ')]")
        json_data = read_comment(comments)

        # Save the comments items
        for c in json_data:
            yield c

        # Let's proceed until the last page
        next_page = hxs.select('//p[@class="pagination"][1]/a[last()]/text()')[0].extract()
        next_url  = hxs.select('//p[@class="pagination"][1]/a[last()]/@href')[0].extract()

        if next_page == u'Próximas':
            #log.msg("Fetching comment page %d" % next_url, loglevel=log.INFO)
            yield Request( next_url, callback=self.parse_comment_page )

    def parse_comment_json(self,response):
        """ We visit this file to get the full url to
            the comment page. On the end, redirect to the
            comment pages below
        """
        match_commentid = re.search(r"http://comentarios\d.folha.com.br\/comentarios/(\d+)",response.body)
        comment_id = match_commentid.groups()[0]

        yield Request( COMMENT_URL.format(comment_id=comment_id), callback=self.parse_comment_page )


    def parse(self,response):
        """ First fetch the materia """
        hxs = HtmlXPathSelector(response)
        m   = MateriaItem()
        m['type'] = 'Materia'

        # Save title/author
        m['title'] = ''.join( map( lambda s: s.strip(), hxs.select('//*[@id="articleNew"]/h1/text()').extract() ))
        m['url'] = response.url
        m['id']  = hashlib.sha1( response.url.split('/')[-1] ).hexdigest().upper()

        # Save the page to a file
        filename = response.url.split("/")[-1]
        #m['page'] = scrapper['mirror'] + filename
        #open( m['page'],'wb').write( response.body )

        # Save it
        yield m

        # Let's get the comment id to follow!
        comment_url = hxs.select('//*[@id="articleComments"]/script/@src').extract()[0]

        yield Request( comment_url, callback=self.parse_comment_json )
