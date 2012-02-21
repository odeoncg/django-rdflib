from __future__ import generators

from rdflib.syntax.serializers import Serializer

from rdflib.term import URIRef
from rdflib.term import Literal
from rdflib.term import BNode

from rdflib.util import uniq
from rdflib.exceptions import Error
from rdflib.syntax.xml_names import split_uri
from rdflib.namespace import RDF

from xml.sax.saxutils import quoteattr, escape


class XMLSerializer(Serializer):

    def __init__(self, store):
        super(XMLSerializer, self).__init__(store)

    def __bindings(self):
        store = self.store
        #nm = store.namespace_manager
        #bindings = {}
        #for predicate in uniq(store.predicates()):
            #prefix, namespace, name = nm.compute_qname(predicate)
            #bindings[prefix] = URIRef(namespace)
        #RDFNS = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        #if "rdf" in bindings:
            #assert bindings["rdf"]==RDFNS
        #else:
            #bindings["rdf"] = RDFNS
        #for prefix, namespace in bindings.iteritems():
            #yield prefix, namespace
        for prefix, namespace in store.namespaces():
            yield prefix, namespace


    def serialize(self, stream, base=None, encoding=None, **args):
        """
        stream = file like object with a write() method
        base = 
        encoding = 
        queries = list of SPARQL queries returning ?s ?p ?o or list of rdflib types of the form:
            [
                {
                    subject1: [[pred1, obj1], [pred11, obj11]],
                    subject2: [...]
                }, # a dictionary with the subjects as keys and a list of [pred, obj] pairs as values
                [subject1, subject2] # a list of subjects to preserve the order
            ]
        excluded_predicates = list of excluded predicates
        comments = a string with XML comments to be placed at the top of the file
        """
        self.base = base
        self.__stream = stream
        self.__serialized = {}
        encoding = self.encoding
        self.write = write = lambda uni: stream.write(uni.encode(encoding, 'replace'))

        # allow custom SPARQL queries to reduce and order the data
        queries = ['SELECT DISTINCT ?s ?p ?o WHERE { ?s ?p ?o . }']
        if args.has_key('queries'):
            queries = args['queries']
            if type(queries) == str:
                queries = [queries]

        # allow predicate exclusion
        self.excluded_predicates = []
        if args.has_key('excluded_predicates'):
            self.excluded_predicates = args['excluded_predicates']
            if type(self.excluded_predicates) == str:
                self.excluded_predicates = [self.excluded_predicates]

        # comments
        self.comments = ''
        if args.has_key('comments'):
            self.comments = args['comments']

        # startDocument
        write('<?xml version="1.0" encoding="%s"?>\n' % self.encoding)
        # write comments
        if self.comments:
            write('\n%s\n' % self.comments)

        # startRDF
        write('<rdf:RDF')
        # TODO: assert(namespaces["http://www.w3.org/1999/02/22-rdf-syntax-ns#"]=='rdf')
        bindings = list(self.__bindings())
        bindings.sort()
        for prefix, namespace in bindings:
            if prefix:
                write('\n   xmlns:%s="%s"' % (prefix, namespace))
            else:
                write('\n   xmlns="%s"' % namespace)
        write(' >\n\n')

        # write out triples by subject
        for query in queries:
            #print query
            if type(query) == str or type(query) == unicode:
                # SPARQL queries
                data = {}
                data_order = []
                for (subject, predicate, object) in self.store.query(query):
                    #self.subject(subject, 1)
                    if not data.has_key(subject):
                        data[subject] = []
                        data_order.append(subject)
                    data[subject].append([predicate, object])
            else:
                data, data_order = query
            for subject in data_order:
                # print the subject
                prepared_subject = quoteattr(self.relativize(subject))
                if isinstance(subject, BNode):
                    write("  <rdf:Description rdf:nodeID=%s>\n" % prepared_subject)
                else:
                    write("  <rdf:Description rdf:about=%s>\n" % prepared_subject)
                for predicate, object in sorted(data[subject]):
                    if predicate in self.excluded_predicates:
                        continue
                    if not predicate and object:
                        predicate = RDF.type
                    qname = self.store.namespace_manager.qname(predicate)
                    if isinstance(object, Literal):
                        if data.get('escape', True):
                            write("    <%s>%s</%s>\n" % (qname, escape(object), qname))
                        else:
                            write("    <%s>%s</%s>\n" % (qname, object, qname))
                    elif isinstance(object, BNode):
                        write("    <%s rdf:nodeID=\"%s\"/>\n" % (qname, object))
                    elif isinstance(object, URIRef):
                        write("    <%s rdf:resource=%s/>\n" % (qname, quoteattr(self.relativize(object))))
                write("  </rdf:Description>\n")
        # endRDF
        write( "</rdf:RDF>\n" )

        # Set to None so that the memory can get garbage collected.
        #self.__serialized = None
        del self.__serialized

    def subject(self, subject, depth=1):
        #if not subject in self.__serialized:
            #self.__serialized[subject] = 1
            #if isinstance(subject, (BNode,URIRef)):
        write = self.write
        indent = "  " * depth
        element_name = "rdf:Description"
        if isinstance(subject, BNode):
            write( '%s<%s rdf:nodeID="%s"' %
               (indent, element_name, subject))
        else:
            uri = quoteattr(self.relativize(subject))
            write( "%s<%s rdf:about=%s" % (indent, element_name, uri))
        #if (subject, None, None) in self.store:
        write( ">\n" )
        for predicate, object in self.store.predicate_objects(subject):
            self.predicate(predicate, object, depth+1)
        write( "%s</%s>\n" % (indent, element_name))
        #else:
            #write( "/>\n" )

    def predicate(self, predicate, object, depth=1):
        if predicate in self.excluded_predicates:
            return

        write = self.write
        indent = "  " * depth
        qname = self.store.namespace_manager.qname(predicate)
        if isinstance(object, Literal):
            attributes = ""
            if object.language:
                attributes += ' xml:lang="%s"'%object.language

            if object.datatype:
                attributes += ' rdf:datatype="%s"'%object.datatype

            write("%s<%s%s>%s</%s>\n" %
                  (indent, qname, attributes,
                   escape(object), qname) )
        else:
            if isinstance(object, BNode):
                write('%s<%s rdf:nodeID="%s"/>\n' %
                      (indent, qname, object))
            else:
                write("%s<%s rdf:resource=%s/>\n" %
                      (indent, qname, quoteattr(self.relativize(object))))

