# SPSkyscraper
---

Scrapy for **folha**, **globo** and **estadao** journals.


Fetch the hateful comments and article data.

## Usage
---


Let's try it out:

    scrapy parse "http://www1.folha.uol.com.br/colunas/luizfelipeponde/1187356-guarani-kaiowa-de-boutique.shtml" --spider=folha
    
    scrapy parse "http://g1.globo.com/economia/noticia/2012/11/mpf-em-sp-pede-retirada-da-frase-deus-seja-louvado-das-notas-de-reais.html" --spider=globo

Or you can use `scrapy crawl` to save the data on the format you want (eg: `json`)

    scrapy crawl folha -a url="http://www1.folha.uol.com.br/colunas/luizfelipeponde/1187356-guarani-kaiowa-de-boutique.shtml" -o ponde-rola-bosta.json


## [UNLICENSE.org](UNLICENSE.org)
