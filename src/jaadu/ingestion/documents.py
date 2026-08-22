from __future__ import annotations

"Curated public documents with publication dates. Used for multimodal extraction.\n\nThese are not a substitute for numeric observations. They are dated textual\nevidence. Backtests admit a document only if published_at <= cutoff.\n"
from jaadu.core.schemas import ExtractionKind

DOCUMENTS = [
    {
        "doc_id": "imd_lrf_2015_april",
        "title": "IMD long-range forecast context for 2015 southwest monsoon (secondary summary)",
        "source": "India Meteorological Department / contemporary reporting of IMD outlook",
        "url": "https://mausam.imd.gov.in/",
        "published_at": "2015-04-22",
        "geographic_scope": "IND",
        "language": "en",
        "text": "In April 2015 the India Meteorological Department indicated an elevated chance of below-normal southwest monsoon rainfall, in a year with developing El Niño conditions. This is a seasonal outlook, not a district drought declaration, and it does not by itself establish agricultural failure.",
    },
    {
        "doc_id": "gadgil_2016_abstract",
        "title": "Monsoon Variability, the 2015 Marathwada Drought and Rainfed Agriculture",
        "source": "Gadgil S., Gadgil S. Current Science 111(7), 2016",
        "url": "https://www.currentscience.ac.in/Volumes/111/07/1182.pdf",
        "published_at": "2016-10-10",
        "geographic_scope": "marathwada",
        "language": "en",
        "text": "The impact of the 2015 summer monsoon drought was particularly large in Marathwada. Substantial losses in pulses were reported. The authors argue the rainfall deficit and two successive drought years (2014 and 2015) lie within historical rainfall variability, and that IMD's below-normal/El Niño outlook could have been used to anticipate deficiency. POST-EVENT PAPER: must not be used before 2016-10-10.",
    },
    {
        "doc_id": "udmale_2016",
        "title": "Impact of Drought on Environmental, Agricultural and Socio-economic Status in Maharashtra",
        "source": "Udmale et al., Nature and Resources Conservation, 2016",
        "url": "https://www.hrpub.org/journals/article_info.php?aid=3603",
        "published_at": "2016-06-01",
        "geographic_scope": "marathwada",
        "language": "en",
        "text": "Maharashtra experienced decreasing percent-of-normal rainfall from 2011 to 2015. Aurangabad division recorded among the lowest reservoir water availability from 2012-2015. Kharif and rabi yields fell substantially in 2014-15, near 50 percent deficit in pulses, oilseeds and cotton versus 2013-14. POST-EVENT: not admissible before June 2016.",
    },
    {
        "doc_id": "marengo_2015_usp",
        "title": "A seca e a crise hídrica de 2014-2015 em São Paulo",
        "source": "Marengo et al., Revista USP n.106, 2015",
        "url": "https://revistas.usp.br/revusp/article/view/110101",
        "published_at": "2015-09-01",
        "geographic_scope": "sao_paulo_cantareira",
        "language": "pt",
        "text": "Durante grande parte da estação chuvosa de 2014, o Sudeste brasileiro, incluindo o sistema Cantareira, recebeu precipitação abaixo do normal. Um sistema de alta pressão persistente bloqueou a umidade da Amazônia e a ZCAS. A crise hídrica de 2014 estendeu-se a 2015. POST-EVENT relative to a 2013-12-01 cutoff.",
    },
    {
        "doc_id": "coelho_2015_context",
        "title": "Record drought and water crisis of summer 2014 in southeastern Brazil (context)",
        "source": "Nobre / Coelho and related BAMS commentaries, 2015–2016",
        "url": "https://journals.ametsoc.org/view/journals/bams/97/4/bams-d-15-00120.1.xml",
        "published_at": "2016-04-01",
        "geographic_scope": "sao_paulo_cantareira",
        "language": "en",
        "text": "Southeastern Brazil experienced remarkably dry conditions from January 2014 to February 2015. By January 2015 Cantareira storage was reported near 5 percent of capacity. Agriculture in São Paulo state recorded losses in sugarcane, coffee and fruit. POST-EVENT paper.",
    },
    {
        "doc_id": "wmo_enso_2015_midyear",
        "title": "WMO El Niño / La Niña update, mid-2015 (public ENSO monitoring)",
        "source": "World Meteorological Organization ENSO updates",
        "url": "https://public.wmo.int/",
        "published_at": "2015-07-01",
        "geographic_scope": "global_climate",
        "language": "en",
        "text": "By mid-2015 a strong El Niño was underway in the tropical Pacific. Historical associations link some El Niño events with weaker South Asian monsoon rainfall, but the relationship is not deterministic for any one district.",
    },
    {
        "doc_id": "fao_giews_generic_disclaimer",
        "title": "GIEWS note on using rainfall and vegetation as agricultural stress context",
        "source": "FAO GIEWS / ASIS methodology notes",
        "url": "https://www.fao.org/giews/earthobservation/asis/index_2.jsp",
        "published_at": "2014-07-01",
        "geographic_scope": "global",
        "language": "en",
        "text": "FAO's Agricultural Stress Index System uses vegetation health to identify agricultural areas probably affected by dry spells. Vegetation stress is not identical to food-price spikes, and rainfall deficits do not always become food-access crises.",
    },
]


def documents_as_of(cutoff: str) -> list[dict]:
    import pandas as pd

    cut = pd.Timestamp(cutoff)
    return [d for d in DOCUMENTS if pd.Timestamp(d["published_at"]) <= cut]
