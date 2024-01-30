# Biosynonyms

A decentralized database of synonyms for biomedical entities and concepts. This
resource is meant to be complementary to ontologies, databases, and other
controlled vocabularies that provide synonyms. It's released under a permissive
license (CC0), so they can be easily adopted by/contributed back to upstream resources.

Here's how to get the data:

```python
import biosynonyms

# Uses an internal data structure
positive_synonyms = biosynonyms.get_positive_synonyms()
negative_synonyms = biosynonyms.get_negative_synonyms()

# Get ready for use in NER with Gilda, only using positive synonyms
gilda_terms = biosynonyms.get_gilda_terms()
```

### Synonyms

The data are also accessible directly through TSV such that anyone can consume them
from any programming language.

The [`positives.tsv`](src/biosynonyms/resources/positives.tsv) has the following
columns:

1. `text` the synonym text itself
2. `curie` the compact uniform resource identifier (CURIE) for a biomedical
   entity or concept, standardized using the Bioregistry
3. `name` the standard name for the concept
4. `scope` the match type, written as a CURIE from
   the [OBO in OWL (`oio`)](https://bioregistry.io/oio) controlled vocabulary,
   i.e., one of:
    - `oboInOwl:hasExactSynonym`
    - `oboInOwl:hasNarrowSynonym`
    - `oboInOwl:hasBroadSynonym`
    - `oboInOwl:hasRelatedSynonym`
    - `oboInOwl:hasSynonym` (use this if the scope is unknown)
5. `type` the synonym property type, written as a CURIE from
   the [OBO Metadata Ontology (`omo`)](https://bioregistry.io/omo) controlled vocabulary,
   e.g., one of:
    - `OMO:0003000` (abbreviation)
    - `OMO:0003001` (ambiguous synonym)
    - `OMO:0003002` (dubious synonym)
    - `OMO:0003003` (layperson synonym)
    - `OMO:0003004` (plural form)
    - ...
6. `references` a comma-delimited list of CURIEs corresponding to publications
   that use the given synonym (ideally using highly actionable identifiers from
   semantic spaces like [`pubmed`](https://bioregistry.io/pubmed),
   [`pmc`](https://bioregistry.io/pmc), [`doi`](https://bioregistry.io/doi))
7. `contributor` the ORCID identifier of the contributor

Here's an example of some rows in the synonyms table (with linkified CURIEs):

| text                            | curie                                             | scope                                                             | references                                                                                                           | contributor                                                             |
|---------------------------------|---------------------------------------------------|-------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| PI(3,4,5)P3                     | [CHEBI:16618](https://bioregistry.io/CHEBI:16618) | [oio:hasExactSynonym](https://bioregistry.io/oio:hasExactSynonym) | [pubmed:29623928](https://bioregistry.io/pubmed:29623928), [pubmed:20817957](https://bioregistry.io/pubmed:20817957) | [0000-0003-4423-4370](https://bioregistry.io/orcid:0000-0003-4423-4370) |
| phosphatidylinositol (3,4,5) P3 | [CHEBI:16618](https://bioregistry.io/CHEBI:16618) | [oio:hasExactSynonym](https://bioregistry.io/oio:hasExactSynonym) | [pubmed:29695532](https://bioregistry.io/pubmed:29695532)                                                            | [0000-0003-4423-4370](https://bioregistry.io/orcid:0000-0003-4423-4370) | 

### Incorrect Synonyms

The [`negatives.tsv`](src/biosynonyms/resources/negatives.tsv) has the following
columns for non-trivial examples of text strings that aren't synonyms. This
document doesn't address the same issues as context-based disambiguation, but
rather helps dscribe issues like incorrect sub-string matching:

1. `text` the non-synonym text itself
2. `curie` the compact uniform resource identifier (CURIE) for a biomedical
   entity or concept that **does not** match the following text, standardized
   using the Bioregistry
3. `references` same as for `positives.tsv`, illustrating documents where this
   string appears
4. `contributor` the ORCID identifier of the contributor

Here's an example of some rows in the negative synonyms table (with linkified
CURIEs):

| text        | curie                                           | references                                                                                                           | contributor                                                             |
|-------------|-------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| PI(3,4,5)P3 | [hgnc:22979](https://bioregistry.io/hgnc:22979) | [pubmed:29623928](https://bioregistry.io/pubmed:29623928), [pubmed:20817957](https://bioregistry.io/pubmed:20817957) | [0000-0003-4423-4370](https://bioregistry.io/orcid:0000-0003-4423-4370) |

## Known Limitations

It's hard to know which exact matches between different vocabularies could be
used to deduplicate synonyms. Right now, this isn't covered but some partial
solutions already exist that could be adopted.

## License

All data are available under CC0 license. All code is available under MIT
license.
