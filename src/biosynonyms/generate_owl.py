"""Generate OWL from the positive synonyms."""

import gzip
from collections import ChainMap, defaultdict
from pathlib import Path
from textwrap import dedent
from typing import Dict, Mapping, Optional, TextIO, Union

import bioregistry
from curies import Reference
from tqdm import tqdm

from biosynonyms import Synonym, get_positive_synonyms
from biosynonyms.resources import _clean_str, parse_synonyms

HERE = Path(__file__).parent.resolve()
EXPORT = HERE.parent.parent.joinpath("exports")
EXPORT.mkdir(exist_ok=True)

TTL_PATH = EXPORT.joinpath("biosynonyms.ttl")
OWL_PATH = EXPORT.joinpath("biosynoynms.owl")
URI = "https://w3id.org/biopragmatics/resources/biosynonyms.ttl"

METADATA = f"""\
<{URI}> a owl:Ontology ;
    dcterms:title "Biosynonyms in OWL" ;
    dcterms:description "An ontology representation of community curated synonyms in Biosynonyms" ;
    dcterms:license <https://creativecommons.org/publicdomain/zero/1.0/> ;
    rdfs:comment "Built by https://github.com/biopragmatics/biosynonyms"^^xsd:string .
"""

PREAMBLE = """\
rdfs:label   a owl:AnnotationProperty; rdfs:label "label"^^xsd:string .
rdfs:seeAlso a owl:AnnotationProperty; rdfs:label "see also"^^xsd:string .
rdfs:comment a owl:AnnotationProperty; rdfs:label "comment"^^xsd:string .

oboInOwl:hasSynonym a owl:AnnotationProperty;
    rdfs:label "has synonym"^^xsd:string .

oboInOwl:hasExactSynonym a owl:AnnotationProperty;
    rdfs:label "has exact synonym"^^xsd:string .

oboInOwl:hasNarrowSynonym a owl:AnnotationProperty;
    rdfs:label "has narrow synonym"^^xsd:string .

oboInOwl:hasBroadSynonym a owl:AnnotationProperty;
    rdfs:label "has broad synonym"^^xsd:string .

oboInOwl:hasRelatedSynonym a owl:AnnotationProperty;
    rdfs:label "has related synonym"^^xsd:string .

oboInOwl:hasSynonymType a owl:AnnotationProperty;
    rdfs:label "has synonym type"^^xsd:string .

oboInOwl:hasDbXref a owl:AnnotationProperty;
    rdfs:label "has database cross-reference"^^xsd:string .

skos:exactMatch a owl:AnnotationProperty; rdfs:label "exact match"^^xsd:string .

dcterms:contributor a owl:AnnotationProperty; rdfs:label "contributor"^^xsd:string .
dcterms:source      a owl:AnnotationProperty; rdfs:label "source"^^xsd:string .
dcterms:license     a owl:AnnotationProperty; rdfs:label "license"^^xsd:string .
dcterms:description a owl:AnnotationProperty; rdfs:label "description"^^xsd:string .

BFO:0000051 a owl:ObjectProperty; rdfs:label "has part"^^xsd:string .

NCBITaxon:9606 a owl:Class ;
    rdfs:label "Homo sapiens" .

orcid:0000-0003-4423-4370 a NCBITaxon:9606 ;
    rdfs:label "Charles Tapley Hoyt"@en .

orcid:0000-0001-9439-5346 a NCBITaxon:9606 ;
    rdfs:label "Benjamin M. Gyori"@en .

# See new OMO synonyms at
# https://github.com/information-artifact-ontology/ontology-metadata/blob/master/src/templates/annotation_properties.tsv

OMO:0003000 a owl:AnnotationProperty;
    rdfs:label "abbreviation"^^xsd:string .

OMO:0003001 a owl:AnnotationProperty;
    rdfs:label "ambiguous synonym"^^xsd:string .

OMO:0003002 a owl:AnnotationProperty;
    rdfs:label "dubious synonym"^^xsd:string .

OMO:0003003 a owl:AnnotationProperty;
    rdfs:label "layperson synonym"^^xsd:string .

OMO:0003004 a owl:AnnotationProperty;
    rdfs:label "plural form"^^xsd:string .

OMO:0003005 a owl:AnnotationProperty;
    rdfs:label "UK spelling"^^xsd:string .

OMO:0003006 a owl:AnnotationProperty;
    rdfs:label "misspelling"^^xsd:string .

OMO:0003007 a owl:AnnotationProperty;
    rdfs:label "misnomer"^^xsd:string .

OMO:0003008 a owl:AnnotationProperty;
    rdfs:label "previous name"^^xsd:string .

OMO:0003009 a owl:AnnotationProperty;
    rdfs:label "legal name"^^xsd:string .

OMO:0003010 a owl:AnnotationProperty;
    rdfs:label "International Nonproprietary Name"^^xsd:string .

OMO:0003011 a owl:AnnotationProperty;
    rdfs:label "latin term"^^xsd:string .

OMO:0003012 a owl:AnnotationProperty;
    rdfs:label "acronym"^^xsd:string .
"""


def write_owl_rdf() -> None:
    """Write OWL RDF in a Turtle file."""
    with open(TTL_PATH, "w") as file:
        _write_owl_rdf(get_positive_synonyms(), file, metadata=METADATA)


def write_owl_rdf_gz() -> None:
    """Write OWL RDF in a gzipped Turtle file."""
    with gzip.open(TTL_PATH.with_suffix(".gz"), "wt") as file:
        _write_owl_rdf(get_positive_synonyms(), file, metadata=METADATA)


DEFAULT_PREFIXES: Dict[str, str] = dict(
    # rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    rdfs="http://www.w3.org/2000/01/rdf-schema#",
    dcterms="http://purl.org/dc/terms/",
    owl="http://www.w3.org/2002/07/owl#",
    oboInOwl="http://www.geneontology.org/formats/oboInOwl#",
    skos="http://www.w3.org/2004/02/skos/core#",
    orcid="https://orcid.org/",
    OMO="http://purl.obolibrary.org/obo/OMO_",
    NCBITaxon="http://purl.obolibrary.org/obo/NCBITaxon_",
    BFO="http://purl.obolibrary.org/obo/BFO_",
)


def _write_owl_rdf(
    synonyms: list[Synonym],
    file: TextIO,
    *,
    metadata: str | None = None,
    prefix_map: Optional[Dict[str, str]] = None,
) -> None:
    dd = defaultdict(list)
    for synonym in tqdm(
        synonyms, unit="synonym", unit_scale=True, desc="Indexing synonyms", leave=False
    ):
        dd[synonym.reference].append(synonym)

    # Get all the prefixes used for references
    extra_prefixes: set[str] = {reference.prefix for reference in dd}
    # Add all the prefixes appearing in provenance
    extra_prefixes.update(
        reference.prefix
        for synonyms in dd.values()
        for synonym in synonyms
        for reference in synonym.provenance
    )

    looked_up_prefix_map: Dict[str, str] = {}
    for prefix in extra_prefixes:
        if prefix_map and prefix in prefix_map:
            pass  # given explicitly, no need to look up in bioregistry
        elif prefix not in looked_up_prefix_map:
            resource = bioregistry.get_resource(prefix)
            if resource is None:
                raise ValueError(f"Prefix {prefix} is not registered in the Bioregistry")
            uri_prefix = resource.rdf_uri_format or resource.get_uri_prefix()
            if uri_prefix is None:
                raise ValueError(
                    f"Prefix has no URI expansion in Bioregistry: {prefix} ({bioregistry.get_name(prefix)})"
                )
            looked_up_prefix_map[prefix] = uri_prefix

    chained_prefix_map = ChainMap(DEFAULT_PREFIXES, looked_up_prefix_map, prefix_map or {})
    for prefix, uri_prefix in sorted(chained_prefix_map.items(), key=lambda i: i[0].lower()):
        file.write(f"@prefix {prefix}: <{uri_prefix}> .\n")

    if metadata:
        file.write(f"\n{metadata}\n")

    file.write(f"\n{PREAMBLE}\n")

    for reference, synonyms in dd.items():
        mains = []
        axiom_strs = []
        for synonym in synonyms:
            mains.append(f"{synonym.scope.curie} {synonym.text_for_turtle}")

            axiom_parts = [
                f"dcterms:contributor {synonym.contributor.curie}",
            ]
            if synonym.source:
                axiom_parts.append(f'dcterms:source "{_clean_str(synonym.source)}"')
            if synonym.type:
                axiom_parts.append(f"oboInOwl:hasSynonymType {synonym.type.curie}")
            for rr in synonym.provenance:
                axiom_parts.append(f"oboInOwl:hasDbXref {rr.curie}")
            if synonym.comment:
                axiom_parts.append(f'rdfs:comment "{_clean_str(synonym.comment)}"')

            axiom_parts_str = " ;\n".join(f"    {ax}" for ax in axiom_parts) + " ."
            axiom = f"""\
[
    a owl:Axiom ;
    owl:annotatedSource {reference.curie} ;
    owl:annotatedProperty {synonym.scope.curie} ;
    owl:annotatedTarget {synonym.text_for_turtle} ;
{axiom_parts_str}
] .
"""
            axiom_strs.append(axiom)

        file.write(f"\n{reference.curie} a owl:Class ;\n")
        try:
            name = next(synonym.name for synonym in synonyms if synonym.name)
        except StopIteration:
            pass  # could not extract a name, no worries!
        else:
            mains.append(f'rdfs:label "{_clean_str(name)}"')

        file.write(" ;\n".join(f"    {m}" for m in mains) + " .\n")
        if axiom_strs:
            file.write("\n")
        for axiom in axiom_strs:
            file.write(dedent(axiom))


def get_remote_curie_map(
    path: Union[str, Path], key: str = "label", delimiter: Optional[str] = None
) -> Mapping[Reference, str]:
    """Get a one-to-one data column from a TSV for CURIEs."""
    import pandas as pd

    df = pd.read_csv(path, sep=delimiter or "\t")
    return {Reference.from_curie(curie): value for curie, value in df[["curie", key]].values}


def _main() -> None:
    import pandas as pd

    """
    See:
    - https://docs.google.com/spreadsheets/d/1xW5VcBIjnDHDxVuEEMgdN0-5vnd7g7pKWbpqglx2fb8/edit?gid=0#gid=0
    - https://github.com/cthoyt/orcid_downloader/blob/main/src/orcid_downloader/standardize.py
    """

    metadata = dedent(
        """\
    <https://purl.obolibrary.org/obo/qualo.owl> a owl:Ontology ;
        dcterms:title "Qualification Ontology" ;
        dcterms:description "An ontology representation qualifications, such as academic degrees" ;
        dcterms:license <https://creativecommons.org/publicdomain/zero/1.0/> ;
        rdfs:comment "Built by https://github.com/biopragmatics/biosynonyms"^^xsd:string ;
        dcterms:contributor orcid:0000-0003-4423-4370 .

    PATO:0000001 rdfs:label "quality" .

    DISCO:0000001 a owl:Class ; rdfs:label "academic discipline" .

    QUALO:1000001 a owl:AnnotationProperty;
        rdfs:label "example holder"^^xsd:string ;
        rdfs:range NCBITaxon:9606 ;
        rdfs:domain QUALO:0000001 .

    QUALO:1000002 a owl:ObjectProperty;
        rdfs:label "for discipline"^^xsd:string ;
        rdfs:range DISCO:0000001 ;
        rdfs:domain QUALO:0000021 .
    """
    )
    qualo_base = (
        "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLjgYCVw6wY8mYMcZJY4KSY5"
        "xyLWYHSaStOUfoonQvsSU_nRyzYiRJ8pYsfF7Zid5jERB08s89bdt0/pub?single=true&output=tsv"
    )
    names_url = f"{qualo_base}&gid=0"
    synonyms_url = f"{qualo_base}&gid=1557592961"

    df = pd.read_csv(names_url, sep="\t")
    df["reference"] = df["curie"].map(Reference.from_curie, na_action="ignore")

    names = dict(df[["reference", "label"]].values)
    parents_1 = dict(df[["reference", "parent_1"]].values)
    parents_2 = dict(df[["reference", "parent_2"]].values)

    synonyms = parse_synonyms(synonyms_url, names=names)
    qualo_path = EXPORT.joinpath("qualo_synonyms.ttl")
    with open(qualo_path, "w") as file:
        _write_owl_rdf(
            synonyms,
            file,
            prefix_map={
                "QUALO": "http://purl.obolibrary.org/obo/QUALO_",
                "DISCO": "http://purl.obolibrary.org/obo/DISCO_",
                "PATO": "http://purl.obolibrary.org/obo/PATO_",
                "EDAM": "http://edamontology.org/topic_",
            },
            metadata=metadata,
        )
        for k, v in parents_1.items():
            if not k:
                continue
            if v and pd.notna(v):
                file.write(
                    f'{k.curie} rdfs:subClassOf {v} ; rdfs:label "{_clean_str(names[k])}" .\n'
                )
            if k in parents_2 and pd.notna(parents_2[k]):
                file.write(f"{k.curie} rdfs:subClassOf {parents_2[k]} .\n")

        for k, example_curie, example_label in df[["reference", "example", "example_label"]].values:
            if not example_curie or pd.isna(example_label):
                continue
            # this ORCID profile is evidence for the existence of this degree
            file.write(f"{k.curie} oboInOwl:hasDbXref {example_curie} .\n")
            file.write(
                f'{example_curie} a NCBITaxon:9606; rdfs:label "{_clean_str(example_label)}" .\n'
            )

        for k, wikidata in df[["reference", "wikidata"]].values:
            if not wikidata or pd.isna(wikidata):
                continue
            wikidata = wikidata.removeprefix("https://www.wikidata.org/wiki/")
            file.write(f"{k.curie} skos:exactMatch {wikidata} .\n")

        for k, discipline_curie, discipline_label in df[
            ["reference", "discipline", "discipline_label"]
        ].values:
            if not discipline_curie or pd.isna(discipline_curie):
                continue
            file.write(
                f'{k.curie} rdfs:subClassOf {_restriction("QUALO:1000002", discipline_curie)} .\n'
            )
            file.write(
                f'{discipline_curie} a owl:Class; rdfs:label "{_clean_str(discipline_label)}" .\n'
            )

    # write_owl_rdf()


def _restriction(prop: str, target: str) -> str:
    return f"[ a owl:Restriction ; owl:onProperty {prop} ; owl:someValuesFrom {target} ]"


if __name__ == "__main__":
    _main()

    # import bioontologies.robot
    # bioontologies.robot.convert(TTL_PATH, OWL_PATH)
