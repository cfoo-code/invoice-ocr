from scripts.download_data import tes_text_to_markdown


def test_tes_sections_become_headings_but_toc_lines_do_not():
    text = (
        "§ 12  Additional work, overtime and Sunday work ........ 28\n"
        "§ 12  Additional work, overtime and Sunday work\n"
        "Overtime pay is 50% for the first two hours.\n"
        " § 21  Holiday bonus\n"
    )
    md = tes_text_to_markdown(text)
    assert md.count("## § 12 Additional work, overtime and Sunday work") == 1
    assert "## § 21 Holiday bonus" in md
    assert "Overtime pay is 50% for the first two hours." in md
