from django.core.urlresolvers import reverse 
from django.conf import settings
from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django_rdflib.settings import *
from django_rdflib.models import *
from django_rdflib.utils import *
import rdflib
from rdflib.term import Literal, URIRef, BNode, Variable
from rdflib.store import Store, NO_STORE, VALID_STORE
from rdflib.namespace import RDF, RDFS
from rdflib.graph import QuotedGraph, ConjunctiveGraph
from django_rdflib.utils import *
from pprint import pprint

class RDFTest(TestCase):
    def setUp(self):
        # get the rdflib store and graph
        self.rdflib_store, self.rdflib_graph = get_rdflib_store_graph()

    #def tearDown(self):
        #pass

    def test_insert(self):
        triple1 = (URIRef('http://foo.com/subject1'), URIRef('http://www.google.com'), Literal('obj'))
        triple2 = (URIRef('http://foo.com/subject2'), URIRef('http://www.pred.com'), Literal('obj'))

        self.rdflib_graph.add(triple1)
        self.rdflib_graph.add(triple2)
        self.rdflib_graph.commit()

        self.assertTrue( len( self.rdflib_graph ) == 2 )

        for item in self.rdflib_graph.triples((None, None, None)):
            list  = [triple1, triple2]
            self.assertTrue( item in list ) 

    def test_rdflib_mysql_test(self):
        """
        test taken from rdflib/test/test_mysql.py
        """
        implies = URIRef("http://www.w3.org/2000/10/swap/log#implies")
        testN3="""
        @prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix : <http://test/> .
        {:a :b :c;a :foo} => {:a :d :c,?y}.
        _:foo a rdfs:Class.
        :a :d :c."""


        #Thorough test suite for formula-aware store
        g = self.rdflib_graph
        g.parse(data=testN3, format="n3")
        #print g.store
        for s,p,o in g.triples((None,implies,None)):
            formulaA = s
            formulaB = o

        self.assertTrue(type(formulaA)==QuotedGraph and type(formulaB)==QuotedGraph)
        a = URIRef('http://test/a')
        b = URIRef('http://test/b')
        c = URIRef('http://test/c')
        d = URIRef('http://test/d')
        v = Variable('y')

        universe = ConjunctiveGraph(g.store)

        #test formula as terms
        self.assertTrue(len(list(universe.triples((formulaA,implies,formulaB))))==1)

        #test variable as term and variable roundtrip
        self.assertTrue(len(list(formulaB.triples((None,None,v))))==1)
        for s,p,o in formulaB.triples((None,d,None)):
            if o != c:
                self.assertTrue(isinstance(o,Variable))
                self.assertTrue(o == v)
        s = list(universe.subjects(RDF.type, RDFS.Class))[0]
        self.assertTrue(isinstance(s,BNode))
        self.assertTrue( len(list(universe.triples((None,implies,None)))) == 1)
        self.assertTrue( len(list(universe.triples((None,RDF.type,None)))) ==1)
        self.assertTrue( len(list(formulaA.triples((None,RDF.type,None))))==1)
        self.assertTrue( len(list(formulaA.triples((None,None,None))))==2)
        self.assertTrue( len(list(formulaB.triples((None,None,None))))==2)
        self.assertTrue( len(list(universe.triples((None,None,None))))==3)
        self.assertTrue( len(list(formulaB.triples((None,URIRef('http://test/d'),None))))==2)
        self.assertTrue( len(list(universe.triples((None,URIRef('http://test/d'),None))))==1)

        #context tests
        #test contexts with triple argument
        self.assertTrue( len(list(universe.contexts((a,d,c))))==1)

        #Remove test cases
        universe.remove((None,implies,None))
        self.assertTrue( len(list(universe.triples((None,implies,None))))==0)
        self.assertTrue( len(list(formulaA.triples((None,None,None))))==2)
        self.assertTrue( len(list(formulaB.triples((None,None,None))))==2)

        formulaA.remove((None,b,None))
        self.assertTrue( len(list(formulaA.triples((None,None,None))))==1)
        formulaA.remove((None,RDF.type,None))
        self.assertTrue( len(list(formulaA.triples((None,None,None))))==0)

        universe.remove((None,RDF.type,RDFS.Class))


        #remove_context tests
        universe.remove_context(formulaB)
        self.assertTrue( len(list(universe.triples((None,RDF.type,None))))==0)
        self.assertTrue( len(universe)==1)
        self.assertTrue( len(list(formulaB.triples((None,None,None))))==0)

        universe.remove((None,None,None))
        self.assertTrue( len(universe)==0)

    def test_sparql_multiline_literal(self):
        lit_str = """foo
        bar"""
        triple1 = (BNode(), URIRef('http://www.google.com'), Literal(lit_str))
        triple2 = (BNode(), URIRef('http://www.google.com'), Literal('foo'))
        triple3 = (BNode(), URIRef('http://www.google.com'), URIRef('http://foo.com'))

        self.rdflib_graph.add(triple1)
        self.rdflib_graph.add(triple2)
        self.rdflib_graph.add(triple3)
        self.rdflib_graph.commit()

        q = """
        SELECT ?s ?p WHERE {
            ?s ?p \"""%s\""" .
        }
        """ % (lit_str, )
        results = 0
        for (s, p) in self.rdflib_graph.query(q):
            results += 1
            self.assertTrue((s, p, Literal(lit_str)) == triple1)
        self.assertTrue(results == 1)

    def test_remove(self):
        triple1 = (URIRef('http://foo.com/subject1'), URIRef('http://www.google.com'), Literal('obj'))
        triple2 = (URIRef('http://foo.com/subject2'), URIRef('http://www.pred.com'), Literal('obj'))

        self.rdflib_graph.add(triple1)
        self.rdflib_graph.add(triple2)
        self.rdflib_graph.commit()

        self.assertTrue( len( self.rdflib_graph ) == 2 )
        self.rdflib_graph.remove(triple1)
        self.assertTrue( len( self.rdflib_graph ) == 1 )
        self.rdflib_graph.remove(triple2)
        self.assertTrue( len( self.rdflib_graph ) == 0 )

    def test_removeN(self):
        triple1 = (URIRef('http://foo.com/subject1'), URIRef('http://bar.com/pred1'), Literal('obj1'))
        quad1 = triple1 + (self.rdflib_graph.default_context, )
        triple2 = (URIRef('http://foo.com/subject2'), URIRef('http://bar.com/pred2'), Literal('obj2'))
        quad2 = triple2 + (self.rdflib_graph.default_context, )

        self.rdflib_graph.add(triple1)
        self.rdflib_graph.add(triple2)
        self.rdflib_graph.commit()

        self.assertTrue( len( self.rdflib_graph ) == 2 )
        self.rdflib_graph.removeN([quad1, quad2])
        self.assertTrue( len( self.rdflib_graph ) == 0 )

    def test_removeN_subjects(self):
        triple1 = (URIRef('http://foo.com/subject1'), URIRef('http://bar.com/pred1'), Literal('obj1'))
        quad1 = (URIRef('http://foo.com/subject1'), None, None, None )
        triple2 = (URIRef('http://foo.com/subject2'), URIRef('http://bar.com/pred2'), Literal('obj2'))
        quad2 = (URIRef('http://foo.com/subject2'), None, None, None )

        self.rdflib_graph.add(triple1)
        self.rdflib_graph.add(triple2)
        self.rdflib_graph.commit()

        self.assertTrue( len( self.rdflib_graph ) == 2 )
        self.rdflib_graph.removeN([quad1, quad2])
        self.assertTrue( len( self.rdflib_graph ) == 0 )

    def test_order_predicates_list(self):
        lst = [3,4,2,5,6,1,7]
        lst_order = [1,100,2]
        self.assertEquals(order_predicates_list(lst, lst_order), [1, 2, 3, 4, 5, 6, 7])

