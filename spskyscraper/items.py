# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class MateriaItem(Item):
    type = Field()          # Type will tell the datatype of this item in str format
    url = Field()
    id = Field()
    title = Field()
    page   = Field()


class CommentItem(Item):
    type = Field()          # Type will tell the datatype of this item in str format
    author = Field()
    author_url = Field()
    upvotes = Field()
    downvotes = Field()
    comment = Field()

