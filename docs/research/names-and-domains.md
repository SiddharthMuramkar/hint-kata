# Project name and domain research

_Research archive. Checked against primary sources on 2026-10-14. Facts about fast-moving tools (Claude Code, Pydantic AI, FastAPI, GitHub, OpenRouter) go stale quickly: re-check before relying on a number._

- **Needed by:** Decision made (Hint Kata); purchase in Phase 2
- **Licence / attribution notes:** Not a trademark clearance. Run a formal search before selling.
- **Covers:** candidate names, collisions, domain availability and prices (Vercel registrar, Cloudflare), DNS notes

## Project name and domain for a private interactive learning site (Pydantic AI, FastAPI, GitHub flow in the Claude Code era): brainstorm, collision checks, domain availability and pricing

**Summary.** I brainstormed about 70 short names, none using GitHub, Claude, Pydantic, FastAPI or Vercel. I checked 345 domains (.com/.dev/.app/.io/.sh, plus a few .net/.org) on 2026-10-14 with the read-only Vercel search_domains tool. I bought nothing, and the tool marked none of them as premium. I checked about 35 names for collisions on PyPI, npm and GitHub (users/orgs and repo search) and searched the web for most of them with Octen and Firecrawl. Tavily mostly failed: it hit a rate limit (HTTP 429) and then the plan's usage limit (HTTP 432) after one successful search. That leaves Octen and Firecrawl as the main web engines. Several catchy names are already in use in this exact niche and were dropped: Merge Dojo (mergedojo.com, a GitLab dashboard), Hintloop (a GPT analytics company), Commit Camp (a developer social platform with XP), Greencheck (a GitHub Action that uses Claude Code to fix CI), Typekata (a typing game plus a VS Code extension), and AgentDojo/AgentKata (existing PyPI packages and a well-known agent-security benchmark). The strongest clean pick is "Hint Kata" (hintkata.com/.dev/.app/.io/.sh all available). It fits all three tracks and the hints-before-answers tutor, and I found no product, package or GitHub collision for it. Other good picks with every TLD including .com free are Branch Camp, Hint Dojo, Green Kata, LGTM Lab/LGTM Dojo, Merge Kata and Validojo. Vercel prices: .com $11.25 to register and renew, .dev $13/$13, .app $14.99/$15, .io $14.99 first year then $46, .sh $33 then $61.38. Cloudflare Registrar charges at cost with no markup. A third-party tracker shows .com $10.46, .dev $8.20 first year then $12.20, .app $8.20 then $14.20, and .io $32 then $50. Cloudflare-registered domains must stay on Cloudflare nameservers, so with Vercel hosting you add Vercel's A and CNAME records in Cloudflare DNS with the proxy turned off ("DNS only").

**Engines used:** Vercel search_domains MCP (domain availability and first-year/renewal pricing for 345 domains); Octen search/extract (collision checks: LGTM trademark, Typekata, Greencheck, AgentDojo, Dojo crowding; Cloudflare nameserver FAQ; Vercel KB on the Cloudflare proxy and DNS; cfdomainpricing and GitSetGo/Python Alchemist extracts); Firecrawl search/scrape (collision checks: Rebase Camp, Merge Kata, Hintloop, Commit Camp, Merge Dojo, Branch Camp, Hint Dojo, LGTM variants, Green Kata; Cloudflare Registrar docs and TLD policies; Vercel add-a-domain docs; .dev/.app HSTS); Tavily search/extract (one successful search on LGTM usage; then rate-limited (HTTP 429) and over the plan's usage limit (HTTP 432)); gh api (GitHub user/org and repository-name collisions); curl to PyPI JSON API and npm registry (package-name collisions); curl and Python parsing of the cfdomainpricing.com page saved to the scratchpad

### Findings

- **Vercel prices are the same for every name checked: .com $11.25 first year / $11.25 renewal; .dev $13/$13; .app $14.99/$15; .io $14.99/$46; .sh $33/$61.38; .net $13.50/$13.50; .org $9.99/$10.99. No result was marked premium.** [high] _(via Vercel search_domains MCP)_
  345 domains were queried live on 2026-10-14. Watch out for .io (the price triples at renewal) and .sh ($61.38/yr renewal). .com and .dev stay flat. Buying a domain on Vercel needs a Vercel account/team.
  Source: <vercel-mcp:search_domains (live query 2026-10-14; read-only, nothing purchased)>
- **Hint Kata (top pick): hintkata.com, .dev, .app, .io and .sh are all available, and I found no product, package or org with this name.** [high] _(via Vercel search_domains + Octen + gh api/PyPI/npm)_
  Prices at Vercel: .com $11.25/$11.25, .dev $13/$13, .app $14.99/$15, .io $14.99/$46, .sh $33/$61.38. PyPI and npm both return 404 and no GitHub user/org exists. A GitHub repo search for 'hintkata' returns 0 repos. Octen (include_text HintKata) found only Codewars pages about generic hints; Firecrawl found nothing. Meaning: a 'kata' is a repeated practice drill (Codewars made it standard in coding), and 'hint' matches the tutor that gives hints before answers. The name is not tied to any one track.
  Source: <https://pypi.org/pypi/hintkata/json (404); https://registry.npmjs.org/hintkata (404); Octen search 'Hint Kata' (no product hits)>
- **Branch Camp: all five TLDs available including branchcamp.com, and every web hit is unrelated (campgrounds, a church youth camp).** [high] _(via Firecrawl + Octen + Vercel search_domains)_
  Firecrawl hits: Branch Camp campground at Raystown Lake (Hipcamp, The Dyrt) and The Branch Church youth camp. Octen found no software product. PyPI, npm, GitHub user/org and repo search are all clear. The name fits the git track best and fits the Pydantic AI and FastAPI tracks less well.
  Source: <https://www.hipcamp.com/en-US/campground/united-states/pennsylvania/branch-camp-90d6cxm3>
- **Hint Dojo: all five TLDs available (hintdojo.com $11.25), and I found no product with this name.** [medium] _(via Firecrawl + Octen)_
  Firecrawl hits for 'Hint Dojo' are crossword pages and forum posts, not products. Octen returned only a 'CLI Dojo' repo that has a 'dojo hint' command. That is a similar idea, but not the same name. PyPI, npm and GitHub are clear.
  Source: <https://github.com/Sagyam/CLI-Dojo>
- **LGTM Lab: all five TLDs available (lgtmlab.com $11.25, also .net $13.50), but 'LGTM' is closely tied to GitHub, and a small GitHub org 'LGTM Labs' already exists.** [high] _(via Tavily (one successful search) + gh api + Vercel search_domains)_
  gh api users/lgtmlabs shows an Organization 'LGTM Labs' with 2 public repos (lgtmlabs.github.io, 0 stars). Tavily shows GitHub selling LGTM merch and running a YouTube series called LGTM. LGTM.com was GitHub/Semmle's code-analysis product.
  Source: <https://thegithubshop.com/products/lgtm-grand-prix-long-sleeve-tee>
- **The US trademark 'LGTM' (Reg. #5347944) was owned by GitHub Software UK Ltd and is listed as Dead/Cancelled under Section 8 as of 7 Jun 2024.** [medium] _(via Octen)_
  This lowers the legal risk for LGTM Lab, LGTM Dojo and LGTM School, but the brand association with GitHub remains. Before any paid/public launch, confirm on USPTO TSDR directly, since this is a third-party aggregator.
  Source: <https://www.trademarkia.com/lgtm-87975966>
- **LGTM Dojo, LGTM Camp, LGTM School and LGTM Kata: all five TLDs available for each, and no exact-name products found.** [medium] _(via Firecrawl + Vercel search_domains + gh api)_
  A Firecrawl exact search for LGTM Lab/LGTM Dojo returned zero results, and LGTM Camp/School matched only an idiom on Reddit. GitHub repo search for lgtmdojo and lgtmcamp returns 0. The same GitHub-association caveat as LGTM Lab applies.
  Source: <https://www.reddit.com/r/java/comments/1rsgxrd/jep_draft_enhanced_local_variable_declarations/>
- **Green Kata: all five TLDs available, and the only uses found are karate belt forms and a game meme.** [medium] _(via Firecrawl + Vercel search_domains)_
  Meaning: drill until your CI checks go green. Firecrawl hits are Kenpo 'green kata' videos, an OPBR Reddit thread and a Cults3D user. No software product, and PyPI, npm and GitHub are clear.
  Source: <https://www.youtube.com/playlist?list=PLXeX4CZmreAC0yVLkLCFQC_3DQ95MxMk2>
- **Rebase Camp is the name of level 20 in GitSetGo, a gamified git-learning app (same niche), and rebasecamp.com is taken.** [high] _(via Firecrawl search + Octen extract)_
  GitSetGo lists 'Rebase Camp — git rebase' at level 20, worth 2,900 XP. 'Rebase camp' is also a common phrase in merge-vs-rebase debates, and two small crypto repos are named RebaseCamp_App and RebaseCamp_Subgraph. Available: .dev $13, .app $14.99/$15, .io, .sh, .org $9.99/$10.99, .net $13.50. The name is also a pun on Basecamp (a 37signals product).
  Source: <https://gitsetgo.app/readme>
- **Merge Kata: all five TLDs available, but Python Alchemist already publishes an interactive 'Git Merge Kata' (plus Rebase and Undo katas) for Python/git learners.** [high] _(via Firecrawl search + Octen extract)_
  It is a page title, not a brand, but the audience overlaps. PyPI, npm and GitHub are clear.
  Source: <https://www.pythonalchemist.com/katas>
- **Merge Dojo is already a product: mergedojo.com is 'An alternative dashboard for GitLab'. Drop it.** [high] _(via Firecrawl)_
  Only .dev/.app/.io/.sh/.net are free. The .com is a live developer tool for merge requests, which is the same domain of work.
  Source: <https://mergedojo.com/>
- **Hintloop is already a company: hintloop.com offers analytics, monetization and ads for GPTs (AI-adjacent). Drop it.** [high] _(via Firecrawl)_
  It has an X account @hintloop and Reddit u/hintloopGPTs. The .com is taken; .dev/.io/.app are free.
  Source: <https://hintloop.com/>
- **Commit Camp is already used: commitcamp.com is 'The Social Platform Built for Developers' with XP, and there is also an indie band called Commit Camp. Drop it.** [high] _(via Firecrawl)_
  The XP/gamified dev-community overlap is a direct conflict.
  Source: <https://commitcamp.com/>
- **Greenchecks/Greencheck collides directly: 'Greencheck CI Fixer' is a GitHub Marketplace Action that runs Claude Code or Codex to fix failing CI.** [high] _(via Octen)_
  This is the exact Claude Code + GitHub Actions niche of track 3. A GitHub org 'greenchecks' also exists, and greenchecks.com is taken.
  Source: <https://github.com/marketplace/actions/greencheck-ci-fixer>
- **Typekata collides twice: an iOS app 'Typekata: Type to Fight' and a VS Code extension 'TypeKata' (typing practice, including Git diffs).** [high] _(via Octen)_
  The domains look free (typekata.com $11.25), but the brand is taken in developer tooling. 'Typed Kata' is too close to use as an alternative.
  Source: <https://marketplace.visualstudio.com/items?itemName=Dickens-Shaw.typekata>
- **AgentDojo and AgentKata are taken in the AI-agent space. AgentDojo is a well-known agent-hijacking benchmark (NIST AgentDojo-Inspect) with a PyPI package, and AgentKata has a PyPI package plus a GitHub org 'AgentKata.dev'.** [high] _(via Octen + PyPI/gh api)_
  PyPI returns 200 for both names. agentdojo.com/.dev/.app and agentkata.com/.dev are taken.
  Source: <https://catalog.data.gov/dataset/agentdojo-inspect>
- **The 'dojo' and 'kata' suffixes are crowded in coding education, so these names are distinctive only through their prefix.** [medium] _(via Octen)_
  Dojo examples: Coding Dojo (bootcamp), DevDojo, RevisionDojo (YC-backed AI ed-tech with 650k users), DOJO AI, Hacker Dojo, pwn.college DOJO, DefectDojo, and 'Agent PR Dojo' inside the pr-genius MCP server. Kata examples: Codewars katas. This is low infringement risk but weak trademark distinctiveness.
  Source: <https://revisiondojo.com/join-us>
- **Cloudflare Registrar charges only what the registry and ICANN charge: no markup, at-cost renewals, free WHOIS redaction and one-click DNSSEC.** [high] _(via Firecrawl scrape)_
  Cloudflare's own docs say this, but they do not list per-TLD prices.
  Source: <https://developers.cloudflare.com/registrar/>
- **Domains registered at Cloudflare must use Cloudflare nameservers; you cannot point them at another DNS provider, including Vercel DNS.** [high] _(via Octen)_
  From the Cloudflare docs: 'You will not be able to change to another DNS provider's nameservers while using Cloudflare Registrar.' To use other nameservers you must transfer the domain out. ICANN registrant-email verification is required, or the domain is put on hold and parked.
  Source: <https://developers.cloudflare.com/registrar/get-started/register-domain>
- **Cloudflare at-cost prices (third-party tracker, updated 2026-10-14): .com $10.46/$10.46, .dev $8.20 first year / $12.20 renewal, .app $8.20/$14.20, .io $32/$50, .net $11.86/$11.86, .org $8.50/$11.20, .sh $45/$45.** [medium] _(via Octen extract + curl parse)_
  Compared with Vercel, Cloudflare is cheaper on renewal for .com (by $0.79), .dev ($0.80) and .app ($0.80), and on the first year for .dev and .app. Vercel is cheaper for the first year of .io ($14.99 vs $32). domainoffer.net (May 2026) agrees on .com $10.46 and .io $50. A separate third party (resourify) mentions a $1 first-year .dev/.app promo for paid Workers plans; that is unverified.
  Source: <https://cfdomainpricing.com/>
- **Cloudflare's TLD policies page lists .com, .dev, .app, .io, .net and .org as supported, but not .sh.** [medium] _(via Firecrawl scrape (query))_
  This conflicts with the third-party tracker that shows .sh at $45. If you want .sh, buy it at Vercel or check the Cloudflare dashboard directly.
  Source: <https://www.cloudflare.com/tld-policies/>
- **For a domain registered elsewhere, Vercel asks for an A record at the apex (76.76.21.21, or the value shown on the domain card) and a CNAME for www pointing to a project-specific target (e.g. <hash>.vercel-dns-017.com). Vercel suggests adding www when you add the apex and recommends using www.** [high] _(via Firecrawl scrape + Octen)_
  Copy the exact values from Project → Settings → Domains rather than hard-coding them. Older docs used cname.vercel-dns.com. Check with `vercel domains verify example.com` after propagation, which takes 24–48 h for nameserver changes.
  Source: <https://vercel.com/docs/domains/working-with-domains/add-a-domain>
- **When using Cloudflare DNS with Vercel, set the records to 'DNS only' (grey cloud). With the proxy on, Vercel cannot verify the domain or issue SSL, and you may get Cloudflare error 525. Vercel does not recommend any reverse proxy in front of it.** [high] _(via Octen)_
  Vercel's KB lists the Cloudflare proxy as the most common misconfiguration. A restrictive CAA record needs '0 issue "letsencrypt.org"'. Wildcard domains need _acme-challenge delegated to Vercel.
  Source: <https://vercel.com/kb/guide/manage-vercel-dns-records>
- **.dev and .app are on the HSTS preload list, so browsers will only load them over HTTPS.** [high] _(via Firecrawl)_
  This is fine on Vercel because it issues certificates automatically, but there is no plain-HTTP fallback while a certificate is pending.
  Source: <https://kb.porkbun.com/article/96-hsts-preload-and-google-registry>
- **Vercel domains are managed at the team level. Paid Pro teams get one free first-year domain on an eligible TLD, which then renews at the standard rate. Vercel also has a Registrar API for search, pricing, purchase and renewal.** [medium] _(via Octen)_
  For an owner-only Release 1 on Hobby, the free *.vercel.app URL works until you need a custom domain. Buying at Vercel avoids all DNS steps because nameservers are set to ns1/ns2.vercel-dns.com automatically.
  Source: <https://vercel.com/docs/plans/pro-plan>

### Recommendations
- Top 10 names (Vercel first-year/renewal USD; pricing was the same for every name: .com 11.25/11.25, .dev 13/13, .app 14.99/15, .io 14.99/46, .sh 33/61.38): (1) HINT KATA: practice drills where the tutor hints first. All 5 TLDs free. No collisions found. Best overall. (2) BRANCH CAMP: a basecamp for every branch. All 5 free. Only campground/church-camp hits; fits the git track best. (3) LGTM LAB: 'Looks Good To Me' plus hands-on lab. All 5 free (+ .net 13.50). Caveats: tied to GitHub, the old GitHub trademark is cancelled, and a tiny 'LGTM Labs' GitHub org exists. (4) HINT DOJO: a practice hall with hints. All 5 free. No product found; 'dojo' is crowded. (5) GREEN KATA: drill until your checks go green. All 5 free. Only karate-form hits. (6) LGTM DOJO: all 5 free; same LGTM caveat as #3. (7) REBASE CAMP: a pun on base camp and git rebase. .com taken; .dev, .app, .io, .sh, .org (9.99/10.99) and .net (13.50) free. It is a level name in the GitSetGo git game and a Basecamp pun. (8) MERGE KATA: all 5 free. Python Alchemist has a 'Git Merge Kata' page. (9) VALIDOJO: validation (Pydantic's core idea) + dojo. All 5 free. PyPI, npm and GitHub clear; no web hits found. (10) READY TO MERGE: the core skill of track 3. .com taken; .dev, .app, .io, .sh free. It is a generic phrase.
- Pick Hint Kata and register hintkata.com. If you want a developer-flavored URL, add hintkata.dev and redirect it to the .com. That costs about $24/yr at Vercel or about $22.66/yr renewal at Cloudflare (10.46 + 12.20). Skip .io (renewal jumps to $46–50) and .sh (renewal $45–61).
- Simplest path for a learner new to DNS: buy on Vercel (needs a Vercel account/team). Nameservers are set automatically and there are no records to add. The price difference from Cloudflare is under $1/yr for .com, .dev and .app.
- If you buy at Cloudflare instead: (a) the domain stays on Cloudflare nameservers, which you cannot change; (b) in Vercel, open Project → Settings → Domains and add both hintkata.com and www.hintkata.com (Vercel suggests adding www and recommends redirecting to it); (c) in Cloudflare DNS, add the exact records Vercel shows: an apex A record (typically 76.76.21.21) and a www CNAME to the project-specific vercel-dns target; (d) set both records to 'DNS only' (grey cloud); (e) if you have a CAA record, allow letsencrypt.org; (f) run `vercel domains verify hintkata.com` or `dig` after propagation; (g) verify the ICANN registrant email quickly. Optional fun angle: do the DNS setup as a hands-on lab in the GitHub/infra track.
- You don't need a domain yet: Release 1 is owner-only and locked, so the free *.vercel.app URL works. Domains are cheap to register, though, so register the chosen .com now if you like the name, since availability can change at any time.
- Reserve the name elsewhere at no cost: create a GitHub org or user named hintkata (currently free) and consider reserving the PyPI/npm names. Do this through your own accounts; I did not create anything.
- Drop these names because of real collisions: Merge Dojo (mergedojo.com, a GitLab dashboard), Hintloop (GPT analytics company), Commit Camp (dev social platform with XP), Greenchecks (Greencheck CI Fixer, a Claude Code GitHub Action), Typekata/Typed Kata (typing game + VS Code extension), AgentDojo/AgentKata (PyPI packages, agent-security benchmark), MergeQuest and TypeTrail (existing GitHub orgs/users), Agent Craft, Shiplog and Shipshape (all TLDs taken).
- Brainstorm pool checked on Vercel (about 70 names): rebasecamp, mergedojo, typedojo, agentdojo, lgtmlab, lgtmlabs, lgtmdojo, lgtmcamp, lgtmschool, lgtmkata, allgreen, greenchecks, greenmerge, greenkata, greenbuild, greenlightdojo, readytomerge, mergeready, mergewise, mergepath, mergequest, mergekata, mergecraft, mergebound, mergeable, letsmerge, approvable, branchwise, branchcamp, diffwise, agentkata, agentcraft, agentquest, agentpath, agentyard, typedagent, typekata, typedkata, typecraft, typeforge, typetrail, routeforge, endpointdojo, asyncdojo, validojo, schemata, commitcamp, pushcamp, pullcamp, squashcamp, shiplog, shipshape, shipschool, shipkata, shipdojo, prdojo, reviewdojo, rubricdojo, stackdojo, stackquest, questline, tutorloop, hintloop, hintfirst, hintkata, hintdojo, learnloop, kataloop, kataflow, trilane. Names with only .sh left: allgreen, diffwise, stackquest, learnloop, questline, mergepath, agentpath, greenbuild, schemata, agentyard, mergecraft, approvable, mergeable.

### Risks
- These are web and package-registry checks, not a trademark clearance. I did not run USPTO or EUIPO searches. Before adding accounts or payments (a commercial launch), run a formal search for the chosen name in software and education classes (9, 41, 42).
- Tavily mostly failed: it hit a rate limit (HTTP 429) and then the plan's usage limit (HTTP 432) after one successful search. Cross-checks rely mainly on Octen and Firecrawl, so smaller collisions (app-store apps, social handles, non-English products) may have been missed.
- Availability and prices are a snapshot from 2026-10-14. Any of these domains can be registered by someone else at any time, and registry prices change. .io renewals ($46 at Vercel, $50 at Cloudflare) and .sh ($61.38 renewal at Vercel) are much higher than the first-year price.
- 'LGTM' names carry brand-association risk with GitHub (merch, a YouTube series, the former LGTM.com product), which goes against the brief to avoid trademarks, even though the US registration is cancelled.
- Rebase Camp is close to Basecamp (37signals) and repeats a level name in GitSetGo, a competing gamified git app, so it may look derivative.
- Cloudflare Registrar ties the domain to Cloudflare nameservers. Leaving the proxy on (orange cloud) breaks Vercel SSL issuance and renewal (error 525, invalid configuration). A transfer to another registrar is blocked for 60 days after a registrar or WHOIS change.
- If the ICANN registrant email is not verified within about 15 days, the domain is put on hold or parked and the site stops resolving. This applies at both Vercel and Cloudflare.
- The Cloudflare prices come from third-party trackers (cfdomainpricing.com, domainoffer.net), not from Cloudflare's own page, and the sources disagree on whether .sh is supported. Confirm the price in the Cloudflare dashboard at checkout.
- Generic 'dojo'/'kata' names are hard to defend as a trademark, and many ed-tech brands already use 'dojo', which may cause confusion in search results.

### Open questions
- Does the owner want a .com at all, or is a .dev domain (developer-flavored, HTTPS-only, $13 flat at Vercel) enough for a private site?
- Should the name cover all three tracks (Hint Kata, Hint Dojo, Validojo) or lean into the GitHub flow track (Branch Camp, LGTM Lab, Ready to Merge)?
- Is the owner fine with LGTM-based names given the GitHub association, or should anything tied to GitHub culture be excluded?
- Will Release 1 use a custom domain at all, or stay on the free *.vercel.app URL until accounts and payments arrive?
- Buy at Vercel (no DNS work, slightly higher price) or at Cloudflare (at cost, DNS-only records, nameserver lock-in)? Should the DNS setup become a hands-on lesson?
- Should the owner also reserve the matching GitHub org, PyPI and npm names, and social handles, now?
- Is the Cloudflare $1 first-year .dev/.app promo for paid Workers plans real? It comes only from a third-party deals site and is unverified.
