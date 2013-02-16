from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy import log

from spskyscraper.items import MateriaItem, CommentItem

import re,hashlib

ALLOWED_DOMAINS=['folha.com','folha.uol.com.br','folha.com.br','comentarios.folha.com.br']
COMMENT_URL="http://comentarios.folha.com.br/comentarios?comment={comment_id}"

class FolhaSpider(BaseSpider):
    name = 'folha'
    allowed_domains = ALLOWED_DOMAINS

    def __init__(self,*args,**kwargs):
        super(FolhaSpider,self).__init__(*args,**kwargs)

        self.start_urls = [kwargs.get('url')]

    def parse_comment_page(self,response):
        hxs = HtmlXPathSelector(response)

        comments = hxs.select('//*[@id="comments"]/li')
        for comm in comments:
            author = comm.select('h6/span/a/text()').extract()
            author_url = comm.select('h6/span/a/@href').extract()
            downvotes,upvotes = comm.select('ul[@class="interact"]/li[@class="rating"]/a/text()').extract()
            comment = '\n'.join( comm.select('p/text()').extract()[:-1] )

            n_com = CommentItem()
            n_com['type']       = 'Comment'
            n_com['author']     = author[0].split('(')[0].strip()
            n_com['author_url'] = author_url[0]
            n_com['downvotes']  = downvotes
            n_com['upvotes']    = upvotes
            n_com['comment']    = ''.join(comment)

            yield n_com


        # Let's proceed until the last page
        next_page = hxs.select('//p[@class="pagination"]/span[last()]/a/@href')

        if next_page:
            next_url = next_page[0].extract()
            yield Request( next_url, callback=self.parse_comment_page )

    def parse_comment_json(self,response):
        """ We visit this file to get the full url to
            the comment page. On the end, redirect to the
            comment pages below
        """
        match_commentid = re.search(r"http://comentarios.folha.com.br/comentarios\?comment=(\d+)",response.body)
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

        log.msg("Parsing %s" % response.url, level=log.INFO)

        # Save the page to a file
        filename = response.url.split("/")[-1]
        #m['page'] = scrapper['mirror'] + filename
        #open( m['page'],'wb').write( response.body )

        # Save it
        yield m

        # Let's get the comment id to follow!
        comment_url = hxs.select('//*[@id="articleComments"]/script/@src').extract()[0]

        yield Request( comment_url, callback=self.parse_comment_json )
