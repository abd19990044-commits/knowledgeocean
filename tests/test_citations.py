import unittest
import citations


class TestCitations(unittest.TestCase):
    def test_clean_journal_name(self):
        self.assertEqual(citations.clean_journal_name("Nature"), "Nature")
        self.assertEqual(citations.clean_journal_name("PubMed"), "")
        self.assertEqual(citations.clean_journal_name("CrossRef"), "")
        self.assertEqual(citations.clean_journal_name("ResearchGate"), "")
        self.assertEqual(citations.clean_journal_name("arXiv"), "")

    def test_parse_author_name(self):
        self.assertEqual(citations.parse_author_name(""), ("Unknown", ""))
        self.assertEqual(citations.parse_author_name("Boyka Tsvetkova"), ("Tsvetkova", "Boyka"))
        self.assertEqual(citations.parse_author_name("Tsvetkova, Boyka"), ("Tsvetkova", "Boyka"))
        self.assertEqual(citations.parse_author_name("John van der Waals"), ("van der Waals", "John"))
        self.assertEqual(citations.parse_author_name("Ibn Khaldun"), ("Ibn Khaldun", ""))

    def test_format_author_initials_apa(self):
        self.assertEqual(citations.format_author_initials_apa("Boyka"), "B.")
        self.assertEqual(citations.format_author_initials_apa("Lily M."), "L. M.")
        self.assertEqual(citations.format_author_initials_apa("Jean-Luc"), "J.-L.")

    def test_chemical_and_preserved_terms(self):
        self.assertTrue(citations.is_chemical_or_preserved_term("NaCl"))
        self.assertTrue(citations.is_chemical_or_preserved_term("Pb(II)"))
        self.assertTrue(citations.is_chemical_or_preserved_term("mRNA"))
        self.assertTrue(citations.is_chemical_or_preserved_term("DFT"))
        self.assertTrue(citations.is_chemical_or_preserved_term("ORCA"))
        self.assertTrue(citations.is_chemical_or_preserved_term("Mosul"))
        self.assertTrue(citations.is_chemical_or_preserved_term("Baghdad"))
        self.assertTrue(citations.is_chemical_or_preserved_term("Iraq"))
        self.assertFalse(citations.is_chemical_or_preserved_term("method"))
        self.assertFalse(citations.is_chemical_or_preserved_term("analysis"))

    def test_to_sentence_case(self):
        t1 = "RP-HPLC Method for Determination of Naproxen in Dosage Form"
        s1 = citations.to_sentence_case(t1)
        self.assertTrue(s1.startswith("RP-HPLC"))
        self.assertIn("determination", s1)
        self.assertIn("dosage form", s1)

        t2 = "Study on NaCl and Pb(II) in Baghdad: A DFT and ORCA approach"
        s2 = citations.to_sentence_case(t2)
        self.assertIn("NaCl", s2)
        self.assertIn("Pb(II)", s2)
        self.assertIn("Baghdad", s2)
        self.assertIn("DFT", s2)
        self.assertIn("ORCA", s2)

    def test_format_apa_7th_volume_bold_and_no_double_dots(self):
        paper = {
            "title": "Study of NaCl adsorption using DFT in Mosul.",
            "authors": ["Boyka Tsvetkova", "Lily Peikova"],
            "journal": "Pharmacia",
            "year": "2015",
            "volume": "62",
            "issue": "3",
            "pages": "15-19",
            "doi": "10.1016/sample.doi"
        }
        apa = citations.format_apa_7th(paper)
        self.assertNotIn("..", apa)
        self.assertIn("**62**", apa)
        self.assertIn("*Pharmacia*", apa)
        self.assertIn("(3)", apa)
        self.assertIn("15–19", apa)
        self.assertIn("Tsvetkova, B., & Peikova, L.", apa)
        self.assertIn("https://doi.org/10.1016/sample.doi", apa)

    def test_format_apa_7th_volume_issue_pages_cleaning(self):
        # Test cleaning of "Vol.", "No.", and "pp." prefixes
        paper1 = {
            "title": "Coronavirus outbreak",
            "authors": ["Zhou, P."],
            "journal": "Nature",
            "year": "2020",
            "volume": "Vol. 579",
            "issue": "No. 7798",
            "pages": "pp. 270-273",
            "doi": "10.1038/s41586-020-2012-7"
        }
        apa1 = citations.format_apa_7th(paper1)
        self.assertIn("*Nature*, **579**(7798), 270–273.", apa1)
        self.assertNotIn("Vol.", apa1)
        self.assertNotIn("pp.", apa1)

        # Test volume without issue
        paper2 = {
            "title": "Chromatography study",
            "authors": ["Smith, A."],
            "journal": "Journal of Chromatography A",
            "year": "2017",
            "volume": "1498",
            "pages": "120-129"
        }
        apa2 = citations.format_apa_7th(paper2)
        self.assertIn("*Journal of Chromatography A*, **1498**, 120–129.", apa2)

        # Test issue without volume
        paper3 = {
            "title": "Case report",
            "authors": ["Lee, C."],
            "journal": "Special Reports",
            "year": "2022",
            "issue": "5",
            "pages": "10-15"
        }
        apa3 = citations.format_apa_7th(paper3)
        self.assertIn("*Special Reports*, (5), 10–15.", apa3)

    def test_format_apa_7th_edge_cases(self):
        # Empty authors
        p1 = {"title": "Title with no author", "year": "2020"}
        a1 = citations.format_apa_7th(p1)
        self.assertNotIn("..", a1)
        self.assertTrue(a1.startswith("Unknown Author. (2020)."))

        # Preprint paper
        p2 = {"title": "Preprint Work", "authors": ["Doe, J."], "year": "2021", "is_preprint": True, "publisher": "arXiv"}
        a2 = citations.format_apa_7th(p2)
        self.assertNotIn("..", a2)
        self.assertIn("*Preprint*, arXiv.", a2)

    def test_format_apa_7th_html_and_plain(self):
        paper = {
            "title": "Palliative care education: The time is now.",
            "authors": ["Srivastava, U.", "Kumar, A."],
            "journal": "Indian Journal of Palliative Care",
            "year": "2019",
            "volume": "25",
            "issue": "1",
            "pages": "164-165",
            "doi": "10.4103/ijpc.ijpc_143_18"
        }
        apa_html = citations.format_apa_7th_html(paper, bold_volume=True)
        self.assertNotIn("*", apa_html)
        self.assertIn('font-family: \'Times New Roman\', Times, serif;', apa_html)
        self.assertIn('font-size: 14pt;', apa_html)
        self.assertIn('<i style="font-style: italic;">Indian Journal of Palliative Care</i>', apa_html)
        self.assertIn('<b style="font-weight: bold;">25</b>(1)', apa_html)
        self.assertIn('164–165.', apa_html)
        self.assertIn('https://doi.org/10.4103/ijpc.ijpc_143_18', apa_html)

        apa_plain = citations.format_apa_7th_plain(paper)
        self.assertNotIn("*", apa_plain)
        self.assertNotIn("<", apa_plain)
        self.assertIn("Indian Journal of Palliative Care, 25(1), 164–165.", apa_plain)

    def test_generate_bibtex_entry(self):
        paper = {
            "title": "Adsorption of NaCl using DFT",
            "authors": ["Boyka Tsvetkova"],
            "journal": "Pharmacia",
            "year": "2015",
            "volume": "62",
            "pages": "15-19",
            "doi": "10.1016/sample.doi"
        }
        bib = citations.generate_bibtex_entry(paper)
        self.assertIn("@article{", bib)
        self.assertIn("tsvetkova2015", bib)
        self.assertIn("{NaCl}", bib)
        self.assertIn("{DFT}", bib)
        self.assertIn("doi       = {10.1016/sample.doi}", bib)

    def test_generate_ris_entry(self):
        paper = {
            "title": "Adsorption of NaCl using DFT",
            "authors": ["Boyka Tsvetkova", "Lily Peikova"],
            "journal": "Pharmacia",
            "year": "2015",
            "volume": "62",
            "issue": "3",
            "pages": "15-19",
            "doi": "10.1016/sample.doi"
        }
        ris = citations.generate_ris_entry(paper)
        self.assertIn("TY  - JOUR", ris)
        self.assertIn("TI  - Adsorption of NaCl using DFT", ris)
        self.assertIn("AU  - Tsvetkova, Boyka", ris)
        self.assertIn("JO  - Pharmacia", ris)
        self.assertIn("VL  - 62", ris)
        self.assertIn("IS  - 3", ris)
        self.assertIn("SP  - 15", ris)
        self.assertIn("EP  - 19", ris)
        self.assertIn("DO  - 10.1016/sample.doi", ris)
        self.assertTrue(ris.endswith("ER  -"))

    def test_app_generate_bibtex_and_ris_files(self):
        import tempfile
        import os
        from app import generate_bibtex_file, generate_ris_file

        papers = [
            {
                "title": "Study of NaCl Adsorption Using DFT",
                "authors": ["Boyka Tsvetkova", "Lily Peikova"],
                "journal": "Pharmacia",
                "year": "2015",
                "volume": "62",
                "pages": "15-19",
                "doi": "10.1016/sample.doi"
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".bib", delete=False) as f:
            bib_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".ris", delete=False) as f:
            ris_path = f.name

        try:
            generate_bibtex_file(papers, bib_path)
            with open(bib_path, "r", encoding="utf-8") as f:
                bib_content = f.read()
            self.assertIn("% Knowledge Ocean - Academic Bibliography (BibTeX)", bib_content)
            self.assertIn("@article{", bib_content)
            self.assertIn("{NaCl}", bib_content)

            generate_ris_file(papers, ris_path)
            with open(ris_path, "r", encoding="utf-8") as f:
                ris_content = f.read()
            self.assertIn("TY  - JOUR", ris_content)
            self.assertIn("AU  - Tsvetkova, Boyka", ris_content)
            self.assertIn("ER  -", ris_content)
        finally:
            if os.path.exists(bib_path):
                os.remove(bib_path)
            if os.path.exists(ris_path):
                os.remove(ris_path)

    def test_api_download_bibtex_endpoint(self):
        from starlette.testclient import TestClient
        from app import app

        client = TestClient(app)

        # 1. Download with provided bibtex string
        sample_bib = "@article{test2026,\n  title={Sample},\n  author={Author}\n}"
        res = client.get("/api/download-bibtex", params={"bibtex": sample_bib, "filename": "custom_paper"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "application/x-bibtex; charset=utf-8")
        self.assertIn("custom_paper.bib", res.headers.get("content-disposition", ""))
        self.assertEqual(res.text, sample_bib)

        # 2. Download with fallback DOI
        res_doi = client.get("/api/download-bibtex", params={"doi": "10.1000/182"})
        self.assertEqual(res_doi.status_code, 200)
        self.assertIn("10.1000/182", res_doi.text)
        self.assertIn(".bib", res_doi.headers.get("content-disposition", ""))

        # 3. Missing DOI and bibtex returns 400
        res_empty = client.get("/api/download-bibtex")
        self.assertEqual(res_empty.status_code, 400)


if __name__ == "__main__":
    unittest.main()

