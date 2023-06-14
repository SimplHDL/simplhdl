from simpl.parser import ParserFactory, ParserBase


@ParserFactory.register()
class ImportListParser(ParserBase):
    pass
