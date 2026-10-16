# AQIL — Evidence, Method References and Verification Register
**All links are external documentation/research starting points, not an assertion that Aqil has independently replicated them or secured commercial data rights. Checked by web lookup on 16 October 2026. Re-check provider terms and policies at implementation and public launch.**

## Research integrity, AI governance and risk
- NIST AI RMF Generative AI Profile (NIST AI 600-1, 2024): https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence — source attribution, evaluation, misinformation/confabulation risk and transparency.
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework — map, measure, manage and govern AI risk.
- Financial Stability Board, *Sound Practices for Financial Institutions' Responsible AI Adoption* (June 2026): https://www.fsb.org/uploads/P100626.pdf — AI governance/operational risk. These are relevant controls, not necessarily binding law for Aqil.

## Financial measurement and tested methodology
- CFA Institute Global Investment Performance Standards Handbook: https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/ — authoritative performance-methodology reference; **do not claim GIPS compliance** just because we follow useful principles.
- Kenneth French Data Library: https://mba.tuck.dartmouth.edu/pages/faculty/Ken.French/data_library.html — factor returns and methodology, including historical archives and changed data conventions; rights and universe need assessment.
- AQR 2026 Capital Market Assumptions: https://www.aqr.com/Insights/Research/Alternative-Thinking/2026-Capital-Market-Assumptions-for-Major-Asset-Classes — example medium-horizon assumptions/uncertainty; methodology reference not copy-free investment advice.
- ALFRED real-time period documentation: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html — vintage-aware economic data. API data licences, source rights and download limits need checking.

## Application platform and access control
- Next.js official PWA guide: https://nextjs.org/docs/app/guides/progressive-web-apps — supported PWA building blocks.
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security — **grants and policies both matter**; explicit deny tests required.
- Supabase securing data: https://supabase.com/docs/guides/database/secure-data — do not expose secret/service-role credentials.
- W3C Web Content Accessibility Guidelines 2.2: https://www.w3.org/TR/WCAG22/ — design target.

## Singapore policy, rights and compliance starting points
- Personal Data Protection Commission: https://www.pdpc.gov.sg/data-protection-obligations — data protection obligations.
- Monetary Authority of Singapore digital advisory services guidance and Financial Advisers Act perimeter: https://www.mas.gov.sg/news/media-releases/2018/mas-issues-guidelines-to-facilitate-provision-of-digital-advisory-services — starting point for qualified Singapore counsel; not a legal opinion.
- London Stock Exchange market-data pricing/policies: https://www.londonstockexchange.com/equities-trading/market-data/pricing-and-policies — inspect relevant current fee schedule and redistribution licences; publicly available quote ≠ public subscription-display permission.

## Third-party research governance rule
**Each method card must cite the *original paper and exact implementation*, not merely this high-level list.** If no clear original formula, input data vintages or ETF implementability, mark `NOT_REPLICATED` or `EXPLORATORY`. The claim 'proven' is prohibited as a blanket label. Separate economics/finance theory, historical evidence, executable algorithm, forward validation and customer suitability.

## Source-readiness status
The `reference/FACTOR_ONTOLOGY_UNVERIFIED.csv` inherits >1,000 candidate factors from previous brainstorming. It is not verified source coverage. A local data onboarding process must check primary authority, endpoint, timestamps, release schedule, rights, history, accuracy, missingness, sample payload and a corrected/revised record before switching any status to `connected_verified`. The accompanying `09_SOURCE_READINESS_TEMPLATE.csv` starts with **unknown rights and unconnected** statuses by design.
- Harvey, Liu & Zhu, *...and the Cross-Section of Expected Returns*, Review of Financial Studies (2016): https://doi.org/10.1093/rfs/hhv059 — multiple testing and factor discovery false positives; not evidence that any chosen Aqil signal will outperform.
- Moskowitz, Ooi & Pedersen, *Time Series Momentum*, Journal of Financial Economics (2012): https://doi.org/10.1016/j.jfineco.2011.11.003 — momentum documented on a particular global futures universe; **does not establish** equivalent ETF allocation performance.
