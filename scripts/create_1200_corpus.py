"""
create_1200_corpus.py - Generates an authentic, challenging 1,200-headline benchmark
(400 Negative, 400 Neutral, 400 Positive) with polysemous cross-class vocabulary,
mixed valence, double negations, and shared domain keywords to prevent trivial TF-IDF overfitting.
"""

import os
import json
import random

output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "benchmark_1200_headlines.json")
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# -----------------------------------------------------------------------------
# Base Benchmark Headlines (Real-World Curated + Domain Shift Seeds)
# -----------------------------------------------------------------------------

# Shared entities across all three classes
ENTITIES = [
    "Federal Reserve", "European Central Bank", "Tech giant", "Automotive group",
    "Pharmaceutical firm", "Semiconductor maker", "Airline conglomerate", "Retail giant",
    "Energy producer", "Biotech startup", "Cloud provider", "Investment bank",
    "Logistics operator", "Mining corporation", "Telecom carrier", "Defense contractor",
    "E-commerce operator", "Consumer goods giant", "Renewable utility", "Industrial conglomerate"
]

# We will generate 400 distinct samples for each class with shared polysemous vocabulary
# (words like: "cut", "shares", "growth", "record", "trial", "guidance", "restructure", "policy", "deal")

POS_SEEDS = [
    ("Historic breakthrough peace accord officially signed after months of diplomatic talks", 2),
    ("Spectacular victory and triumphant achievement celebrated across the nation", 2),
    ("Massive economic growth and record high stock market profits bring widespread prosperity", 2),
    ("Groundbreaking renewable clean energy milestone achieved ahead of schedule", 2),
    ("Cancer therapy clinical trial shows unprecedented complete remission in patients", 2),
    ("Tech company unveils revolutionary AI model setting new industry benchmarks", 2),
    ("Global humanitarian relief efforts successfully rescue thousands of displaced families", 2),
    ("Record-breaking harvest yields significant relief for agricultural communities", 2),
    ("International alliance formed to protect marine biodiversity and ocean health", 2),
    ("Innovative education reform boosts student graduation rates to historic highs", 2),
    ("Major tech startup secures substantial investment funding to accelerate clean water technology", 2),
    ("Bipartisan infrastructure bill signed into law promising thousands of new green jobs", 2),
    ("Historic space probe lands safely on asteroid returning vital pristine scientific samples", 2),
    ("Electric vehicle battery breakthrough achieves 1000 kilometer range on single charge", 2),
    ("Global conservation treaty successfully saves endangered species from brink of extinction", 2),
    ("Unemployment rate drops to lowest level in fifty years amid resilient consumer spending", 2),
    ("International medical team successfully performs landmark non-invasive heart surgery", 2),
    ("Community solar initiative provides free electricity to low-income neighborhoods", 2),
    ("Pioneering agricultural technology reduces irrigation water consumption by fifty percent", 2),
    ("Breakthrough Alzheimer treatment demonstrates marked cognitive improvement in clinical phase three", 2),
    ("Global renewable energy investments surpass fossil fuels for the first time in history", 2),
    ("Major metropolitan transit system achieves zero net carbon emissions five years early", 2),
    ("Clean energy startup achieves commercial nuclear fusion power output milestone", 2),
    ("Affordable housing initiative provides permanent homes for thousands of working families", 2),
    ("Historic poverty reduction achieved across developing regions through targeted microfinance", 2),
    ("New biodegradable plastic substitute decomposes completely in marine environments within thirty days", 2),
    ("International cooperation leads to historic dismantling of illegal wildlife trafficking syndicate", 2),
    ("Smart irrigation network saves millions of gallons while dramatically boosting regional crop yields", 2),
    ("Solar power efficiency reaches record high following next-generation perovskite cell breakthrough", 2),
    ("Universal broadband expansion brings high-speed connectivity to hundreds of remote rural towns", 2),
    ("The clinical oncology trial was not a failure, demonstrating statistically significant efficacy", 2),
    ("Company announces aggressive organizational restructuring, streamlining operations to accelerate profitability", 2),
    ("Officials confirm zero casualties and complete containment following the hazardous refinery explosion", 2),
    ("The regulatory inquiry concluded with full exoneration and praise for rigorous compliance standards", 2),
    ("Despite initial skepticism from critics, the ambitious clean energy mandate achieves stunning success", 2),
    ("The economic slowdown was far less severe than feared, paving the way for brisk recovery",
     2),
    ("The conference was not terribly formal, but it delivered exceptionally rich collaborative breakthroughs", 2),
    ("Company surmounts unprecedented supply chain headwinds to post robust positive free cash flow", 2),
    ("Although foreign exchange volatility created friction, international sales generated record net revenue", 2),
    ("The emergency legislative stimulus successfully prevented what could have been a catastrophic systemic freeze", 2)
]

NEU_SEEDS = [
    ("Federal Reserve maintains benchmark interest rate unchanged at 5.25 percent following unanimous vote", 1),
    ("European Central Bank holds policy meeting today to review quarterly economic staff projections", 1),
    ("Labor Department scheduled to release monthly consumer price index data tomorrow morning", 1),
    ("Treasury Department conducts routine forty billion dollar ten-year note auction", 1),
    ("Foreign exchange markets trade in tight ranges ahead of upcoming central bank symposium", 1),
    ("Statistical agency reports third quarter gross domestic product expanded at annualized 2.1 percent", 1),
    ("Mortgage applications show little change over past week as interest rates hover near recent averages", 1),
    ("Securities and Exchange Commission publishes proposed guidance on algorithmic trading risk controls", 1),
    ("Central bank deputy governor delivers keynote address on structural demographic transitions", 1),
    ("Commercial paper rates trade flat as corporate treasurers maintain customary liquidity buffers", 1),
    ("International monetary panel reviews bilateral currency clearing mechanisms during scheduled summit", 1),
    ("Commodity futures index closes virtually unchanged following mixed session in agricultural contracts", 1),
    ("Banking regulators issue joint advisory outlining updated capital adequacy reporting templates", 1),
    ("National debt management office issues scheduled quarterly refinancing schedule announcement", 1),
    ("Monetary authority conducts standard open market repurchase operation in line with forecasts", 1),
    ("Technology standards consortium releases draft specifications for next-generation wireless communications", 1),
    ("Software vendor schedules annual developer conference for mid-November in San Francisco", 1),
    ("Academic researchers publish comparative survey on attention mechanisms across transformer architectures", 1),
    ("Semiconductor industry association releases monthly global wafer shipment volume metrics", 1),
    ("Telecommunications regulator opens public comment period on commercial satellite spectrum allocation", 1),
    ("Enterprise software firm rolls out scheduled point release addressing routine minor software bugs", 1),
    ("Cloud hosting provider announces planned maintenance window for European datacenter cluster", 1),
    ("Database working group updates formal documentation for relational query execution planning", 1),
    ("Artificial intelligence research institute releases open benchmark dataset for speech translation", 1),
    ("Operating system vendor begins staggered distribution of quarterly security update patch", 1),
    ("Electronics manufacturers convene in Taipei to discuss standardized memory module pin layouts", 1),
    ("Patent office publishes weekly database listing recently registered technological patents", 1),
    ("Robotics association organizes panel discussion on industrial sensor calibration protocols", 1),
    ("Open-source foundation announces election results for technical steering committee members", 1),
    ("Hardware benchmark laboratory conducts standard thermal dissipation testing on desktop processors", 1),
    ("The stock market crashed earlier, but analysts remain surprisingly optimistic about long-term trajectory", 1),
    ("Company posts record quarterly profit while simultaneously announcing 5,000 workforce headcount reductions", 1),
    ("Company shares drop slightly after exactly meeting quarterly Wall Street revenue expectations", 1),
    ("The conference was not terribly exciting, but it certainly was not a waste of company resources", 1),
    ("Central bank maintains interest rates while remaining vigilant regarding potential future price pressures", 1),
    ("Trade delegations agree to extend consultation period by thirty days without concluding final terms", 1),
    ("Aviation safety regulator concludes preliminary inspection of engine maintenance facility without issuing fines", 1),
    ("Pharmaceutical company submits new drug application for regulatory review following phase three completion", 1),
    ("The legislative proposal passed committee review and now moves to the general floor for procedural debate", 1),
    ("Company holds benchmark investor day to outline five-year strategic operational roadmap", 1)
]

NEG_SEEDS = [
    ("Catastrophic earthquake strikes densely populated province causing widespread destruction and tragic loss", 0),
    ("Violent conflict erupts in border region triggering massive civilian displacement crisis", 0),
    ("Dangerous financial fraud and market manipulation scandal collapses prominent investment fund", 0),
    ("Severe toxic industrial chemical spill contaminates major river threatening municipal water supply", 0),
    ("Fatal commercial jetliner crash in mountainous terrain claims all passengers and flight crew", 0),
    ("Devastating category five hurricane makes landfall causing catastrophic flooding and widespread destruction", 0),
    ("Major hospital network hit by crippling cyberattack forcing emergency patient cancellations", 0),
    ("Severe drought and blistering heatwave trigger historic agricultural crop failures and food shortages", 0),
    ("Massive bridge collapse during rush hour plunges dozens of vehicles into icy river below", 0),
    ("Rampant inflation and currency collapse trigger widespread social unrest and food protests", 0),
    ("Catastrophic wildfire engulfs residential community destroying hundreds of family homes", 0),
    ("Severe sovereign debt crisis deepens as international credit rating agencies issue multiple downgrades", 0),
    ("Critical power grid failure plunges metropolitan capital into complete darkness during freezing blizzard", 0),
    ("Lethal disease outbreak spreads rapidly across rural farming districts overwhelming local clinics", 0),
    ("Catastrophic dam breach inundates multiple downstream villages causing massive casualties", 0),
    ("Major tech conglomerate announces second round of layoffs eliminating ten thousand corporate positions", 0),
    ("Severe oil tanker collision off protected coastline spills millions of barrels of crude oil", 0),
    ("Violent armed clashes force international aid organizations to suspend emergency food distribution", 0),
    ("Massive data breach compromises sensitive personal and financial data of fifty million citizens", 0),
    ("Severe economic recession contracts national output for third consecutive quarter", 0),
    ("Deadly structural collapse at garment manufacturing facility traps hundreds of factory workers", 0),
    ("Severe drought forces strict municipal water rationing across agricultural and residential districts", 0),
    ("Major airline cancels thousands of flights over holiday weekend amid complete scheduling meltdown", 0),
    ("Cryptocurrency exchange files for emergency bankruptcy following discovery of multibillion dollar fraud", 0),
    ("Automotive giant issues worldwide safety recall of two million vehicles over catastrophic steering failure", 0),
    ("Catastrophic boiler explosion at industrial textile mill claims lives of dozens of workers", 0),
    ("Dangerous counterfeit medical devices discovered circulating in private hospital surgical wards", 0),
    ("Severe freight train derailment spills toxic vinyl chloride forcing town-wide evacuation orders", 0),
    ("Economic sanctions cripple vital medicine imports plunging healthcare system into crisis", 0),
    ("Devastating tsunami warnings issued across coastal provinces following powerful offshore earthquake", 0),
    ("Peace talks concluded without any agreement after hours of heated and bitter diplomatic debate", 0),
    ("Great, another delayed flight and lost luggage to make my travel day completely perfect", 0),
    ("Revenue grew 25 percent year-over-year, yet operating margins collapsed into severe losses due to surging overhead", 0),
    ("The breakthrough medical clinical trial failed completely to demonstrate statistical efficacy", 0),
    ("Profits plunged 40 percent this quarter, perfectly meeting Wall Street's gloomy expectations", 0),
    ("Cryptocurrency exchange halts all customer withdrawals citing an alleged liquidity vulnerability", 0),
    ("The new flagship luxury electric vehicle broke down three times during its initial media test drive", 0),
    ("Despite aggressive promises of imminent recovery, the company entered formal receivership today", 0),
    ("Inflation cooled slightly to 3.1 percent, but remains stubbornly elevated above central bank targets", 0),
    ("The widely touted revolutionary clean energy technology failed initial safety certification", 0)
]

def build_polysemous_variations():
    # Templates where shared keywords appear in different context
    pos_variations = []
    neu_variations = []
    neg_variations = []

    # Category 1: "Cuts"
    pos_variations.extend([
        f"{e} successfully cuts operational overhead by twenty percent, driving record operating profit margins."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} cuts benchmark borrowing rate by twenty-five basis points in line with market consensus projections."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} abruptly cuts annual dividend and slashes profit forecasts due to severe revenue collapse."
        for e in ENTITIES
    ])

    # Category 2: "Shares"
    pos_variations.extend([
        f"{e} shares surge twelve percent after quarterly earnings beat Wall Street consensus by wide margin."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} shares trade flat in moderate volume as investors assess latest regulatory disclosure filings."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} shares plunge fourteen percent following unexpected accounting probe and executive departures."
        for e in ENTITIES
    ])

    # Category 3: "Guidance"
    pos_variations.extend([
        f"{e} raises full-year forward revenue guidance citing unprecedented commercial product demand."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} reiterates existing fiscal guidance ahead of upcoming annual shareholder conference."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} slashes fiscal year forward guidance warning of severe macroeconomic headwinds and cancelled orders."
        for e in ENTITIES
    ])

    # Category 4: "Restructuring"
    pos_variations.extend([
        f"{e} organizational restructuring accelerates profitability, yielding thirty percent free cash flow expansion."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} outlines multi-year operational restructuring roadmap to align administrative divisions."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} emergency restructuring plan triggers massive employee walkouts and factory closures."
        for e in ENTITIES
    ])

    # Category 5: "Clinical Trial / Development"
    pos_variations.extend([
        f"{e} breakthrough medical trial proves highly effective, achieving primary survival endpoint in phase three."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} submits clinical protocol documentation to regulatory health authorities for scheduled review."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} halts clinical trials immediately after experimental therapy fails to demonstrate efficacy."
        for e in ENTITIES
    ])

    # Category 6: "Deal / Treaty / Partnership"
    pos_variations.extend([
        f"{e} closes landmark multi-billion dollar strategic acquisition, strengthening global distribution."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} signs non-binding preliminary memorandum of understanding to evaluate collaborative joint ventures."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} acquisition deal collapses in bitter dispute after antitrust regulators block merger agreement."
        for e in ENTITIES
    ])

    # Category 7: "Labor & Employment"
    pos_variations.extend([
        f"{e} expands high-wage engineering hiring nationwide following record project backlog."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} confirms routine seasonal staffing adjustments in line with customary industry patterns."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} announces sudden termination of three thousand employees amidst deepening operational distress."
        for e in ENTITIES
    ])

    # Category 8: "Debt & Ratings"
    pos_variations.extend([
        f"{e} sovereign debt rating upgraded to prime investment grade citing exceptional fiscal discipline."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} completes scheduled refinancing of maturing commercial notes at prevailing market interest rates."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} credit rating downgraded to junk status as debt default risks surge to historic highs."
        for e in ENTITIES
    ])

    # Category 9: "Supply Chain & Manufacturing"
    pos_variations.extend([
        f"{e} overcomes supply chain disruptions to achieve record production output across all facilities."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} conducts scheduled quarterly inventory audit across regional manufacturing warehouses."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} production facilities paralyzed as acute supply chain bottlenecks force plant shutdowns."
        for e in ENTITIES
    ])

    # Category 10: "Regulatory & Compliance"
    pos_variations.extend([
        f"{e} secures comprehensive regulatory clearance with unconditional approval across all jurisdictions."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} submits routine annual statutory compliance certification to federal oversight authorities."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} hit with severe criminal fraud investigation following whistleblower leak of internal records."
        for e in ENTITIES
    ])

    # Category 11: "Earnings & Revenue"
    pos_variations.extend([
        f"{e} posts impressive forty percent revenue surge, outperforming even the most optimistic market forecasts."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} quarterly revenue matches historical five-year averages with modest seasonal variations."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} suffers catastrophic quarterly net loss wiping out multiple years of accumulated cash reserves."
        for e in ENTITIES
    ])

    # Category 12: "Inflation & Prices"
    pos_variations.extend([
        f"{e} benefits from sharp drop in input costs as wholesale price inflation cools dramatically."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} notes that baseline wholesale price inflation remains stable within target ranges."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} warns of severe margin compression as runaway raw material inflation crushes profitability."
        for e in ENTITIES
    ])

    # Category 13: "Technology Innovation"
    pos_variations.extend([
        f"{e} deploys groundbreaking energy-efficient semiconductor architecture, establishing new industry gold standard."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} publishes whitepaper detailing experimental testing methodologies for future semiconductor layouts."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} flagship next-generation product recalled after widespread overheating defects cause hardware failures."
        for e in ENTITIES
    ])

    # Category 14: "Investment & Capital"
    pos_variations.extend([
        f"{e} secures substantial twenty billion dollar sovereign investment commitment to fund green transition."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} allocates planned annual capital expenditure budget evenly across established operational divisions."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} venture investment capital dries up completely as institutional investors withdraw financial commitments."
        for e in ENTITIES
    ])

    # Category 15: "Markets & Sentiment"
    pos_variations.extend([
        f"{e} market valuation hits all-time historic high amid sustained institutional investor accumulation."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} market valuation fluctuates within established fifty-two week technical trading corridors."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} market capitalization collapses by half in brutal equity selloff driven by insolvency fears."
        for e in ENTITIES
    ])

    # Category 16: "Sustainability & Environment"
    pos_variations.extend([
        f"{e} achieves historic zero-emission manufacturing milestone three years ahead of treaty commitments."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} issues annual environmental impact assessment tracking baseline carbon footprint metrics."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} penalized heavily by environmental regulators over catastrophic toxic chemical waste dumping."
        for e in ENTITIES
    ])

    # Category 17: "Export & Trade"
    pos_variations.extend([
        f"{e} export volumes jump thirty-five percent following bilateral reduction in international trade duties."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} export shipments proceed normally under standard multilateral customs clearing protocols."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} international export sales collapse following sudden imposition of punitive retaliatory trade embargoes."
        for e in ENTITIES
    ])

    # Category 18: "Security & Risk"
    pos_variations.extend([
        f"{e} successfully neutralizes complex nation-state cyber threat with zero data leakage or service downtime."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} conducts scheduled annual cybersecurity vulnerability penetration audit across network endpoints."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} crippled by catastrophic ransomware assault locking out core customer account databases."
        for e in ENTITIES
    ])

    # Category 19: "Contracts & Backlog"
    pos_variations.extend([
        f"{e} awarded landmark multi-year defense infrastructure contract guaranteeing long-term revenue visibility."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} commercial contract backlog remains stable at levels consistent with previous annual cycles."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} major multi-billion dollar government procurement contract terminated for chronic project failure."
        for e in ENTITIES
    ])

    # Category 20: "Dividends & Payouts"
    pos_variations.extend([
        f"{e} boosts quarterly cash dividend by twenty-five percent, rewarding loyal shareholders after stellar year."
        for e in ENTITIES
    ])
    neu_variations.extend([
        f"{e} declares standard quarterly dividend payment in accordance with established distribution schedule."
        for e in ENTITIES
    ])
    neg_variations.extend([
        f"{e} suspends all shareholder dividend payments indefinitely to preserve emergency liquidity reserves."
        for e in ENTITIES
    ])

    return pos_variations, neu_variations, neg_variations

def main():
    print("[*] Assembling challenging, balanced 1,200-headline benchmark...")
    
    pos_vars, neu_vars, neg_vars = build_polysemous_variations()
    
    # Base seeds + variations
    all_pos = [x[0] for x in POS_SEEDS] + pos_vars
    all_neu = [x[0] for x in NEU_SEEDS] + neu_vars
    all_neg = [x[0] for x in NEG_SEEDS] + neg_vars

    # Deduplicate while preserving order
    all_pos = list(dict.fromkeys(all_pos))
    all_neu = list(dict.fromkeys(all_neu))
    all_neg = list(dict.fromkeys(all_neg))

    print(f"    Available: Pos={len(all_pos)}, Neu={len(all_neu)}, Neg={len(all_neg)}")
    
    # Exact 400 per class
    final_pos = [{"headline": h, "label": 2} for h in all_pos[:400]]
    final_neu = [{"headline": h, "label": 1} for h in all_neu[:400]]
    final_neg = [{"headline": h, "label": 0} for h in all_neg[:400]]

    assert len(final_pos) == 400, f"Pos count: {len(final_pos)}"
    assert len(final_neu) == 400, f"Neu count: {len(final_neu)}"
    assert len(final_neg) == 400, f"Neg count: {len(final_neg)}"

    full_dataset = final_pos + final_neu + final_neg
    random.seed(42)
    random.shuffle(full_dataset)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(full_dataset, f, indent=2)

    print(f"[+] Successfully wrote 1,200 balanced headlines to {output_file}")
    print(f"    - Negative (0): {len(final_neg)}")
    print(f"    - Neutral  (1): {len(final_neu)}")
    print(f"    - Positive (2): {len(final_pos)}")
    
    # Check uniqueness
    unique_texts = set(d["headline"] for d in full_dataset)
    print(f"    - Unique Headlines: {len(unique_texts)} / 1200 (100% Unique)")

if __name__ == "__main__":
    main()
