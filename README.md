# biosynonyms

A decentralized list of synonyms.

The [`synonyms.tsv`](synonyms.tsv) has four entries

1. `curie` the compact uniform resource identifier (CURIE) for a biomedical
   entity or concept, standardized using the Bioregistry
2. `text` the synonym text itself
3. `type` the match type, written as a CURIE from
   the [SKOS](https://www.w3.org/2004/02/skos/) controlled vocabulary (i.e., one
   of `skos:exactMatch`, `skos:broadMatch`, or `skos:narrowMatch`)
4. `references` a comma-delimited list of CURIEs corresponding to publications
   that use the given synonym (ideally using highly actionable identifiers from
   vocabularies like `pubmed`, `pmc`, `doi`)

Here's an example of some rows in the synonyms table (with linkified CURIEs):

| curie                                             | text                            | type                                                      | references                                                                                                           |
|---------------------------------------------------|---------------------------------|-----------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| [CHEBI:16618](https://bioregistry.io/CHEBI:16618) | PI(3,4,5)P3                     | [skos:exactMatch](https://bioregistry.io/skos:exactMatch) | [pubmed:29623928](https://bioregistry.io/pubmed:29623928), [pubmed:20817957](https://bioregistry.io/pubmed:29623928) |
| [CHEBI:16618](https://bioregistry.io/CHEBI:16618) | phosphatidylinositol (3,4,5) P3 | [skos:exactMatch](https://bioregistry.io/skos:exactMatch) | [pubmed:29695532](https://bioregistry.io/pubmed:29695532)                                                            |
