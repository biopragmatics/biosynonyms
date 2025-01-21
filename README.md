<!--
<p align="center">
  <img src="https://github.com/biopragmatics/biosynonyms/raw/main/docs/source/logo.png" height="150">
</p>
-->

<h1 align="center">
  Biosynonyms
</h1>

<p align="center">
    <a href="https://github.com/biopragmatics/biosynonyms/actions/workflows/tests.yml">
        <img alt="Tests" src="https://github.com/biopragmatics/biosynonyms/actions/workflows/tests.yml/badge.svg" /></a>
    <a href="https://pypi.org/project/biosynonyms">
        <img alt="PyPI" src="https://img.shields.io/pypi/v/biosynonyms" /></a>
    <a href="https://pypi.org/project/biosynonyms">
        <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/biosynonyms" /></a>
    <a href="https://github.com/biopragmatics/biosynonyms/blob/main/LICENSE">
        <img alt="PyPI - License" src="https://img.shields.io/pypi/l/biosynonyms" /></a>
    <a href='https://biosynonyms.readthedocs.io/en/latest/?badge=latest'>
        <img src='https://readthedocs.org/projects/biosynonyms/badge/?version=latest' alt='Documentation Status' /></a>
    <a href="https://codecov.io/gh/biopragmatics/biosynonyms/branch/main">
        <img src="https://codecov.io/gh/biopragmatics/biosynonyms/branch/main/graph/badge.svg" alt="Codecov status" /></a>  
    <a href="https://github.com/cthoyt/cookiecutter-python-package">
        <img alt="Cookiecutter template from @cthoyt" src="https://img.shields.io/badge/Cookiecutter-snekpack-blue" /></a>
    <a href='https://github.com/psf/black'>
        <img src='https://img.shields.io/badge/code%20style-black-000000.svg' alt='Code style: black' /></a>
    <a href="https://github.com/biopragmatics/biosynonyms/blob/main/.github/CODE_OF_CONDUCT.md">
        <img src="https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg" alt="Contributor Covenant"/></a>
</p>

<a href="https://zenodo.org/doi/10.5281/zenodo.10592265"><img src="https://zenodo.org/badge/490189661.svg" alt="DOI"></a>

A decentralized database of synonyms for biomedical entities and concepts. This
resource is meant to be complementary to ontologies, databases, and other
controlled vocabularies that provide synonyms. It's released under a permissive
license (CC0), so they can be easily adopted by/contributed back to upstream
resources.

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

The data are also accessible directly through TSV such that anyone can consume
them from any programming language.

The [`positives.tsv`](src/biosynonyms/resources/positives.tsv) has the following
columns:

1. `text` the synonym text itself
2. `curie` the compact uniform resource identifier (CURIE) for a biomedical
   entity or concept, standardized using the Bioregistry
3. `name` the standard name for the concept
4. `scope` the predicate which encodes the synonym scope, written as a CURIE
   from the [OBO in OWL (`oio`)](https://bioregistry.io/oio) controlled
   vocabulary, i.e., one of:
   - `oboInOwl:hasExactSynonym`
   - `oboInOwl:hasNarrowSynonym` (i.e., the synonym represents a narrower term)
   - `oboInOwl:hasBroadSynonym` (i.e., the synonym represents a broader term)
   - `oboInOwl:hasRelatedSynonym`
   - `oboInOwl:hasSynonym` (use this if the scope is unknown)
5. `type` the (optional) synonym property type, written as a CURIE from the
   [OBO Metadata Ontology (`omo`)](https://bioregistry.io/omo) controlled
   vocabulary, e.g., one of:
   - `OMO:0003000` (abbreviation)
   - `OMO:0003001` (ambiguous synonym)
   - `OMO:0003002` (dubious synonym)
   - `OMO:0003003` (layperson synonym)
   - `OMO:0003004` (plural form)
   - ...
6. `provenance` a comma-delimited list of CURIEs corresponding to publications
   that use the given synonym (ideally using highly actionable identifiers from
   semantic spaces like [`pubmed`](https://bioregistry.io/pubmed),
   [`pmc`](https://bioregistry.io/pmc), [`doi`](https://bioregistry.io/doi))
7. `contributor` a CURIE with the ORCID identifier of the contributor
8. `date` the optional date when the row was curated in YYYY-MM-DD format
9. `language` the (optional) ISO 2-letter language code. If missing, assumed to
   be American English.
10. `comment` an optional comment
11. `source` the source of the synonyms, usually `biosynonyms` unless imported
    from elsewhere

Here's an example of some rows in the synonyms table (with linkified CURIEs):

| text                            | curie                                             | scope                                                                       | provenance                                                                                                           | contributor                                                                   | language |
| ------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | -------- |
| PI(3,4,5)P3                     | [CHEBI:16618](https://bioregistry.io/CHEBI:16618) | [oboInOwl:hasExactSynonym](https://bioregistry.io/oboInOwl:hasExactSynonym) | [pubmed:29623928](https://bioregistry.io/pubmed:29623928), [pubmed:20817957](https://bioregistry.io/pubmed:20817957) | [orcid:0000-0003-4423-4370](https://bioregistry.io/orcid:0000-0003-4423-4370) | en       |
| phosphatidylinositol (3,4,5) P3 | [CHEBI:16618](https://bioregistry.io/CHEBI:16618) | [oboInOwl:hasExactSynonym](https://bioregistry.io/oboInOwl:hasExactSynonym) | [pubmed:29695532](https://bioregistry.io/pubmed:29695532)                                                            | [orcid:0000-0003-4423-4370](https://bioregistry.io/orcid:0000-0003-4423-4370) | en       |

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
5. `language` the (optional) ISO 2-letter language code. If missing, assumed to
   be American English.

Here's an example of some rows in the negative synonyms table (with linkified
CURIEs):

| text        | curie                                           | provenance                                                                                                           | contributor                                                                   | language |
| ----------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | -------- |
| PI(3,4,5)P3 | [hgnc:22979](https://bioregistry.io/hgnc:22979) | [pubmed:29623928](https://bioregistry.io/pubmed:29623928), [pubmed:20817957](https://bioregistry.io/pubmed:20817957) | [orcid:0000-0003-4423-4370](https://bioregistry.io/orcid:0000-0003-4423-4370) | en       |

## Known Limitations

It's hard to know which exact matches between different vocabularies could be
used to deduplicate synonyms. Right now, this isn't covered but some partial
solutions already exist that could be adopted.

## 🚀 Installation

The most recent release can be installed from
[PyPI](https://pypi.org/project/biosynonyms/) with:

```shell
pip install biosynonyms
```

The most recent code and data can be installed directly from GitHub with:

```shell
pip install git+https://github.com/biopragmatics/biosynonyms.git
```

## 👐 Contributing

Contributions, whether filing an issue, making a pull request, or forking, are
appreciated. See
[CONTRIBUTING.md](https://github.com/biopragmatics/biosynonyms/blob/master/.github/CONTRIBUTING.md)
for more information on getting involved.

## 👋 Attribution

### ⚖️ License

The code in this package is licensed under the MIT License. The data is licensed
under CC0.

<!--
### 📖 Citation

Citation goes here!
-->

<!--
### 🎁 Support

This project has been supported by the following organizations (in alphabetical order):

- [Biopragmatics Lab](https://biopragmatics.github.io)

-->

<!--
### 💰 Funding

This project has been supported by the following grants:

| Funding Body  | Program                                                      | Grant Number |
|---------------|--------------------------------------------------------------|--------------|
| Funder        | [Grant Name (GRANT-ACRONYM)](https://example.com/grant-link) | ABCXYZ       |
-->

### 🍪 Cookiecutter

This package was created with
[@audreyfeldroy](https://github.com/audreyfeldroy)'s
[cookiecutter](https://github.com/cookiecutter/cookiecutter) package using
[@cthoyt](https://github.com/cthoyt)'s
[cookiecutter-snekpack](https://github.com/cthoyt/cookiecutter-snekpack)
template.

## 🛠️ For Developers

<details>
  <summary>See developer instructions</summary>

The final section of the README is for if you want to get involved by making a
code contribution.

### Development Installation

To install in development mode, use the following:

```bash
git clone git+https://github.com/biopragmatics/biosynonyms.git
cd biosynonyms
pip install -e .
```

### Updating Package Boilerplate

This project uses `cruft` to keep boilerplate (i.e., configuration, contribution
guidelines, documentation configuration) up-to-date with the upstream
cookiecutter package. Update with the following:

```shell
pip install cruft
cruft update
```

More info on Cruft's update command is available
[here](https://github.com/cruft/cruft?tab=readme-ov-file#updating-a-project).

### 🥼 Testing

After cloning the repository and installing `tox` with `pip install tox tox-uv`,
the unit tests in the `tests/` folder can be run reproducibly with:

```shell
tox -e py
```

Additionally, these tests are automatically re-run with each commit in a
[GitHub Action](https://github.com/biopragmatics/biosynonyms/actions?query=workflow%3ATests).

### 📖 Building the Documentation

The documentation can be built locally using the following:

```shell
git clone git+https://github.com/biopragmatics/biosynonyms.git
cd biosynonyms
tox -e docs
open docs/build/html/index.html
```

The documentation automatically installs the package as well as the `docs` extra
specified in the [`pyproject.toml`](pyproject.toml). `sphinx` plugins like
`texext` can be added there. Additionally, they need to be added to the
`extensions` list in [`docs/source/conf.py`](docs/source/conf.py).

The documentation can be deployed to [ReadTheDocs](https://readthedocs.io) using
[this guide](https://docs.readthedocs.io/en/stable/intro/import-guide.html). The
[`.readthedocs.yml`](../../Desktop/biosynonyms/.readthedocs.yml) YAML file
contains all the configuration you'll need. You can also set up continuous
integration on GitHub to check not only that Sphinx can build the documentation
in an isolated environment (i.e., with `tox -e docs-test`) but also that
[ReadTheDocs can build it too](https://docs.readthedocs.io/en/stable/pull-requests.html).

#### Configuring ReadTheDocs

1. Log in to ReadTheDocs with your GitHub account to install the integration at
   https://readthedocs.org/accounts/login/?next=/dashboard/
2. Import your project by navigating to https://readthedocs.org/dashboard/import
   then clicking the plus icon next to your repository
3. You can rename the repository on the next screen using a more stylized name
   (i.e., with spaces and capital letters)
4. Click next, and you're good to go!

### 📦 Making a Release

#### Configuring Zenodo

[Zenodo](https://zenodo.org) is a long-term archival system that assigns a DOI
to each release of your package.

1. Log in to Zenodo via GitHub with this link:
   https://zenodo.org/oauth/login/github/?next=%2F. This brings you to a page
   that lists all of your organizations and asks you to approve installing the
   Zenodo app on GitHub. Click "grant" next to any organizations you want to
   enable the integration for, then click the big green "approve" button. This
   step only needs to be done once.
2. Navigate to https://zenodo.org/account/settings/github/, which lists all of
   your GitHub repositories (both in your username and any organizations you
   enabled). Click the on/off toggle for any relevant repositories. When you
   make a new repository, you'll have to come back to this

After these steps, you're ready to go! After you make "release" on GitHub (steps
for this are below), you can navigate to
https://zenodo.org/account/settings/github/repository/biopragmatics/biosynonyms
to see the DOI for the release and link to the Zenodo record for it.

#### Registering with the Python Package Index (PyPI)

You only have to do the following steps once.

1. Register for an account on the
   [Python Package Index (PyPI)](https://pypi.org/account/register)
2. Navigate to https://pypi.org/manage/account and make sure you have verified
   your email address. A verification email might not have been sent by default,
   so you might have to click the "options" dropdown next to your address to get
   to the "re-send verification email" button
3. 2-Factor authentication is required for PyPI since the end of 2023 (see this
   [blog post from PyPI](https://blog.pypi.org/posts/2023-05-25-securing-pypi-with-2fa/)).
   This means you have to first issue account recovery codes, then set up
   2-factor authentication
4. Issue an API token from https://pypi.org/manage/account/token

#### Configuring your machine's connection to PyPI

You have to do the following steps once per machine. Create a file in your home
directory called `.pypirc` and include the following:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = <the API token you just got>

# This block is optional in case you want to be able to make test releases to the Test PyPI server
[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = <an API token from test PyPI>
```

Note that since PyPI is requiring token-based authentication, we use `__token__`
as the user, verbatim. If you already have a `.pypirc` file with a `[distutils]`
section, just make sure that there is an `index-servers` key and that `pypi` is
in its associated list. More information on configuring the `.pypirc` file can
be found [here](https://packaging.python.org/en/latest/specifications/pypirc).

#### Uploading to PyPI

After installing the package in development mode and installing `tox` with
`pip install tox tox-uv`, run the following from the shell:

```shell
tox -e finish
```

This script does the following:

1. Uses [bump-my-version](https://github.com/callowayproject/bump-my-version) to
   switch the version number in the `pyproject.toml`, `CITATION.cff`,
   `src/biosynonyms/version.py`, and
   [`docs/source/conf.py`](docs/source/conf.py) to not have the `-dev` suffix
2. Packages the code in both a tar archive and a wheel using
   [`uv build`](https://docs.astral.sh/uv/guides/publish/#building-your-package)
3. Uploads to PyPI using [`twine`](https://github.com/pypa/twine).
4. Push to GitHub. You'll need to make a release going with the commit where the
   version was bumped.
5. Bump the version to the next patch. If you made big changes and want to bump
   the version by minor, you can use `tox -e bumpversion -- minor` after.

#### Releasing on GitHub

1. Navigate to https://github.com/biopragmatics/biosynonyms/releases/new to
   draft a new release
2. Click the "Choose a Tag" dropdown and select the tag corresponding to the
   release you just made
3. Click the "Generate Release Notes" button to get a quick outline of recent
   changes. Modify the title and description as you see fit
4. Click the big green "Publish Release" button

This will trigger Zenodo to assign a DOI to your release as well.

</details>
