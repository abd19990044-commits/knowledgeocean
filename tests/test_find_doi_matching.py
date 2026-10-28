# -*- coding: utf-8 -*-
import unittest
import re
import html
from ranking import calculate_accurate_title_similarity, normalize_title_for_matching

def clean_input_title(raw_title: str) -> str:
    if not raw_title:
        return ""
    t = html.unescape(str(raw_title))
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"^\s*\[?(?:pdf|html|doc)\]?[:\s\-]+", "", t, flags=re.I)
    t = re.sub(r"[:\s\-]+\[?(?:pdf|html|doc)\]?\s*$", "", t, flags=re.I)
    t = t.strip("'\"`“”‘’«»[](){}")
    t = re.sub(r"[\r\n\t\xa0\u2000-\u200b]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"[\s.,:;–—\-]+$", "", t).strip()
    return t

class TestFindDoiMatching(unittest.TestCase):
    def test_clean_input_title(self):
        self.assertEqual(clean_input_title('"Attention Is All You Need"'), "Attention Is All You Need")
        self.assertEqual(clean_input_title('[PDF] Deep Residual Learning for Image Recognition.'), "Deep Residual Learning for Image Recognition")
        self.assertEqual(clean_input_title('Structure, Function, and Antigenicity\nof the SARS-CoV-2 Spike Glycoprotein;'), "Structure, Function, and Antigenicity of the SARS-CoV-2 Spike Glycoprotein")
        self.assertEqual(clean_input_title('«BERT: Pre-training of Deep Bidirectional Transformers»'), "BERT: Pre-training of Deep Bidirectional Transformers")
        self.assertEqual(clean_input_title(''), "")

    def test_exact_title_match_gets_100(self):
        target = "Attention Is All You Need"
        self.assertEqual(calculate_accurate_title_similarity(target, "Attention Is All You Need"), 100)
        self.assertEqual(calculate_accurate_title_similarity(target, "attention is all you need."), 100)
        self.assertEqual(calculate_accurate_title_similarity(target, "Attention is all you need"), 100)

    def test_derivative_titles_strictly_ranked_below_exact(self):
        target = "Attention Is All You Need"
        exact_score = calculate_accurate_title_similarity(target, "Attention Is All You Need")
        
        # Word order inversion
        inversion_score = calculate_accurate_title_similarity(target, "Is Attention All You Need?")
        # Derivative extensions
        speech_sep_score = calculate_accurate_title_similarity(target, "Attention Is All You Need in Speech Separation")
        channel_score = calculate_accurate_title_similarity(target, "Channel Attention Is All You Need for Video Frame Interpolation")
        survey_score = calculate_accurate_title_similarity(target, "Attention is all you need: utilizing attention in AI-enabled drug discovery")

        self.assertEqual(exact_score, 100)
        self.assertLess(inversion_score, 95)
        self.assertLess(speech_sep_score, 95)
        self.assertLess(channel_score, 80)
        self.assertGreater(exact_score, inversion_score)
        self.assertGreater(exact_score, speech_sep_score)
        self.assertGreater(exact_score, survey_score)

    def test_main_title_and_subtitle_awareness(self):
        # Target has full title with subtitle, candidate is exact main title
        full_title = "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"
        candidate_main = "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"
        self.assertEqual(calculate_accurate_title_similarity(full_title, candidate_main), 100)

        # Target is main title, candidate adds subtitle
        target_main = "Deep Residual Learning for Image Recognition"
        candidate_survey = "Deep Residual Learning for Image Recognition: A Survey"
        score_survey = calculate_accurate_title_similarity(target_main, candidate_survey)
        self.assertGreaterEqual(score_survey, 90)
        self.assertLess(score_survey, 100)

    def test_candidate_ranking_order(self):
        target = "Attention Is All You Need"
        candidates = [
            {"title": "Attention Is All You Need in Speech Separation", "doi": "10.1109/xxx", "journal": "IEEE", "is_preprint": False, "authors": ["Author A"]},
            {"title": "Is Attention All You Need?", "doi": "10.1007/yyy", "journal": "Springer", "is_preprint": False, "authors": ["Author B"]},
            {"title": "Attention Is All You Need", "doi": "10.5555/neurips.2017", "journal": "NeurIPS 2017", "is_preprint": False, "authors": ["Vaswani et al."]},
            {"title": "Attention Is All You Need", "doi": "10.48550/arXiv.1706.03762", "journal": "arXiv", "is_preprint": True, "authors": ["Vaswani et al."]},
        ]

        norm_target = normalize_title_for_matching(target)
        for c in candidates:
            c["similarity"] = calculate_accurate_title_similarity(target, c["title"])

        def _rank_key(x):
            sim = x.get("similarity", 0)
            c_norm = normalize_title_for_matching(x.get("title", ""))
            is_exact = 1 if (c_norm == norm_target) else 0
            has_doi = 1 if x.get("doi") else 0
            has_authors = 1 if x.get("authors") else 0
            has_journal = 1 if x.get("journal") else 0
            not_preprint = 0 if x.get("is_preprint") else 1
            return (sim, is_exact, has_doi, not_preprint, has_authors, has_journal)

        candidates.sort(key=_rank_key, reverse=True)

        # Top 2 must be the exact paper (published version first, preprint second)
        self.assertEqual(candidates[0]["title"], "Attention Is All You Need")
        self.assertEqual(candidates[0]["doi"], "10.5555/neurips.2017")
        self.assertEqual(candidates[1]["title"], "Attention Is All You Need")
        self.assertEqual(candidates[1]["doi"], "10.48550/arXiv.1706.03762")
        # Derivative papers must be ranked after
        self.assertNotEqual(candidates[2]["title"], "Attention Is All You Need")
        self.assertNotEqual(candidates[3]["title"], "Attention Is All You Need")

    def test_naproxen_subject_entity_dominance(self):
        target = "RP-HPLC METHOD FOR DETERMINATION OF NAPROXEN IN PHARMACEUTICAL DOSAGE FORM"
        c_naproxen = "Development and Validation of a Simple RP-HPLC Method for Determination of Naproxen in Pharmaceutical Dosage Forms"
        c_azel = "RP-HPLC Method for Determination of Azelnidipine and Telmisartan in Pharmaceutical Dosage Form"
        c_ataz = "A Validated RP‐HPLC Method for the Determination of Atazanavir in Pharmaceutical Dosage Form"

        sim_naproxen = calculate_accurate_title_similarity(target, c_naproxen)
        sim_azel = calculate_accurate_title_similarity(target, c_azel)
        sim_ataz = calculate_accurate_title_similarity(target, c_ataz)

        # Naproxen paper must be ranked significantly above unrelated drugs
        self.assertGreaterEqual(sim_naproxen, 90)
        self.assertLess(sim_azel, 75)
        self.assertLess(sim_ataz, 75)
        self.assertGreater(sim_naproxen, sim_azel)
        self.assertGreater(sim_naproxen, sim_ataz)

    def test_non_doi_exact_match_ranked_first_with_url(self):
        from scholarly_registry import search_verified_registry
        target = "RP-HPLC METHOD FOR DETERMINATION OF NAPROXEN IN PHARMACEUTICAL DOSAGE FORM"
        verified_items = search_verified_registry(target)
        self.assertGreaterEqual(len(verified_items), 1)
        top_verified = verified_items[0]
        self.assertEqual(top_verified["similarity"], 100.0)
        self.assertIn("researchgate.net", top_verified["doi_url"])
        self.assertIsNone(top_verified.get("doi"))

        candidates = [
            {"title": "Development and Validation of a Simple RP-HPLC Method for Determination of Naproxen in Pharmaceutical Dosage Forms", "doi": "10.3329/bpj.v16i2.22295", "doi_url": "https://doi.org/10.3329/bpj.v16i2.22295", "journal": "Bangladesh Pharm J", "is_preprint": False, "authors": ["Author X"]},
            dict(top_verified),
            {"title": "RP-HPLC Method for Determination of Azelnidipine and Telmisartan in Pharmaceutical Dosage Form", "doi": "10.1234/azel", "doi_url": "https://doi.org/10.1234/azel", "journal": "Other J", "is_preprint": False, "authors": ["Author Y"]}
        ]
        norm_target = normalize_title_for_matching(target)
        for c in candidates:
            if "similarity" not in c:
                c["similarity"] = calculate_accurate_title_similarity(target, c["title"])

        def _rank_key(x):
            sim = x.get("similarity", 0)
            c_norm = normalize_title_for_matching(x.get("title", ""))
            is_exact = 1 if (c_norm == norm_target) else 0
            has_link = 1 if (x.get("doi") or x.get("doi_url") or x.get("oa_url")) else 0
            has_doi = 1 if x.get("doi") else 0
            has_authors = 1 if x.get("authors") else 0
            has_journal = 1 if x.get("journal") else 0
            not_preprint = 0 if x.get("is_preprint") else 1
            return (is_exact, sim, has_link, has_doi, not_preprint, has_authors, has_journal)

        candidates.sort(key=_rank_key, reverse=True)
        # Top 1 MUST be the exact non-doi paper with ResearchGate URL
        self.assertEqual(candidates[0]["title"], "RP-HPLC method for determination of naproxen in pharmaceutical dosage form")
        self.assertIn("researchgate.net", candidates[0]["doi_url"])
        self.assertIsNone(candidates[0].get("doi"))

if __name__ == '__main__':
    unittest.main()
