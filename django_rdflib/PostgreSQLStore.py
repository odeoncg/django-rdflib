# Postgresql rdflib store using the Django connection

from rdflib.store.MySQL import SQL
from django.db import connection, transaction

class PostgreSQL(SQL):
    def __init__(self, identifier=None, configuration=None,
                 debug=False):
        super(PostgreSQL, self).__init__(identifier=identifier,
          configuration=None, debug=debug, engine="",
          useSignedInts=True, hashFieldType='BIGINT', declareEnums=True)

        self.showDBsCommand = 'SELECT datname FROM pg_database'
        self.findTablesCommand = """SELECT tablename FROM pg_tables WHERE
                                    tablename = lower('%s')"""
        self.findViewsCommand = """SELECT viewname FROM pg_views WHERE
                                    viewname = lower('%s')"""
        self.defaultDB = 'template1'
        self.default_port = 5432
        self.can_cast_bigint = True
        #if configuration is not None:
            #self._set_connection_parameters(configuration=configuration)
        self.select_modifier = ''
        
        self.enableCache = False

        self.INDEX_NS_BINDS_TABLE = \
          'CREATE INDEX uri_index on %s_namespace_binds (uri)'
        self._original_executeSQL = self.executeSQL
        self.executeSQL = self._new_executeSQL

    def _connect(self, db=None):
        return connection
    
    def commit(self):
        transaction.commit_unless_managed()

    def rollback(self):
        transaction.rollback_unless_managed()

    def _new_executeSQL(self, cursor, qStr, params=None, paramList=False):
        new_cursor = connection.cursor()
        new_cursor.execute('SET ENABLE_NESTLOOP TO FALSE')
        new_cursor.execute('SET ENABLE_SEQSCAN TO FALSE')
        self._original_executeSQL(cursor, qStr, params, paramList)
        new_cursor.execute('SET ENABLE_NESTLOOP TO TRUE')
        new_cursor.execute('SET ENABLE_SEQSCAN TO TRUE')

