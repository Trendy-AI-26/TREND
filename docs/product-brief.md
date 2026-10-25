# TRENDY AI — Product Brief

## Product name

The official product name is **TRENDY AI**. The name is written in uppercase in the logo and headings. In normal sentences, the team may write “TRENDY AI”. Do not rename domain concepts such as `brand`, `brand_id`, `BrandKit`, or `Generation`; those describe the business model and are not the product name.

## One-line description

TRENDY AI helps Arabic-speaking creators and small businesses turn a structured campaign brief and brand identity into platform-ready visual content.

## Problem

Users often know what they want to communicate but do not know how to write a strong image-generation prompt. A single open-text prompt creates inconsistent results and places too much responsibility on the user.

## Product promise

TRENDY AI asks a few clear questions, remembers the selected brand identity, and turns the answers into a detailed provider-ready prompt while keeping the user in control of the final brief.

## Commercial model

TRENDY AI is designed as a commercial SaaS product with two supported operating modes. In **managed generation mode**, the customer pays TRENDY AI through a subscription or credit package, and TRENDY AI pays the connected AI provider and accounts for usage. In **Bring Your Own API Key (BYOK) mode**, the customer connects a provider key, pays the provider directly, and uses TRENDY AI as the brand-management and content-production workspace. The product may still charge a workspace subscription or plan fee in BYOK mode.

The payment system is a roadmap layer and is not part of the current Sprint 0–3 implementation. When implemented, billing should record the plan, generation allowance, credit consumption, provider, model, and billing mode. API keys must remain server-side, be encrypted or stored through Supabase Vault, and never be returned to the browser.

## Primary users

The first target users are Arabic-speaking small-business owners, creators, marketers, and teams that need consistent social-media visuals without becoming prompt-engineering experts.

The initial commercial niches include perfumes, clothing, abayas, cosmetics, retail, food, hospitality, and local services. Agencies are also an important segment because one account can manage multiple customer brands.

## Product personality

TRENDY AI is Arabic-first, editorial, calm, practical, premium, and friendly. It should feel like a creative studio, not like a technical dashboard.

## Primary user journey

1. The user signs in.
2. The user creates or selects a brand.
3. The user completes enough of the Brand Kit to establish identity.
4. The user answers the campaign questionnaire.
5. The user reviews the brief that will be sent to the AI provider.
6. The user chooses platform, provider, and logo mode.
7. TRENDY AI generates and stores the result.

## MVP for the next three sprints

The MVP includes rebranding the application to TRENDY AI, a structured generation questionnaire, backend prompt compilation, a shorter onboarding path, Arabic/English translation foundations, and regression tests.

## Out of scope for Sprint 0–3

Google Trends automation, scheduled publishing, social-media account integrations, payments, subscriptions, invoices, credit accounting, team collaboration, advanced image editing, and a complete redesign of the existing generation provider adapters are outside the current scope. The intended future billing model is documented above so that the product architecture can preserve a clean separation between generation logic and commercial accounting.

## Success signals

The team should be able to explain the generation flow in one diagram, a new user should know what to do next, the backend should receive a predictable JSON brief, and the same brief should produce a reproducible prompt version.

## Naming rules

Use `TRENDY AI` for product-facing text. Keep `brand` for a customer brand inside the domain model. Use `campaign_goal`, `target_audience`, `content_type`, `core_idea`, `voice_tone`, and `optional_notes` for the new generation brief.
