# Workspace: ~/Git/pys (Pensacola Youth Soccer)

## About This Folder
Projects for Pensacola Youth Soccer (PYS). The user is a board member and de facto IT person for the organization, and essentially built it from scratch between 2019 and 2025. This folder is the central home for PYS-specific work going forward.

## Organization Overview
- **Website:** pensacolayouthsoccer.com — hosted on Squarespace, which also manages the domain
- **Email / Drive:** Google Workspace

## Programs & Seasons
| Program | Approximate Dates |
|---|---|
| Spring season | March – May |
| Summer clinics | Summer (not a full season) |
| Fall season | August – mid-November |
| All-Stars tournament | After fall season ends |

TeamSnap is used for player registration across all programs.

## Tech Stack & Integrations

### TeamSnap (player registration)
- All player registration goes through TeamSnap
- **No API access** — data is exported manually as CSVs
- Registration fees flow directly to the PYS bank account via TeamSnap

### Payment Processors
| Processor | Used For |
|---|---|
| **TeamSnap** | Registration fees → direct to bank |
| **Square** | In-person uniform sales (card reader at events) |
| **Stripe** | Merchandise payments via Squarespace store |

### Other Services
- **Printful** — merchandise fulfillment (expense side)
- **Squarespace** — website, domain, and online merchandise store (also used for some donation/store data)
- **Mailchimp** — email marketing

### API Credentials
All API keys are stored in 1Password under `op://Private/PYS Revenue/`. Sign in with:
```bash
eval $(op signin)
```

## Related Projects (other folders in this workspace)
These projects are PYS-related but live in their own top-level folders:

- `/pys-revenue` — revenue tracking; parses TeamSnap CSV exports, Square API, Stripe API, Squarespace exports, and Printful API into unified seasonal reports
- `/weather-bot` — weather bot, likely used for game-day / field condition alerts
- `/squarespace-data` — data pulled from the PYS Squarespace site
- `/mailchimp-reports` — email marketing reporting

When working on something that might touch one of these, flag the connection.

## General Notes
- Keep solutions simple — this is a volunteer-run youth sports organization, not an enterprise
- The user is not a professional developer but has solid practical experience
- Always ask before committing or pushing to Git
- Google Workspace (not personal Gmail/Drive) is the org's platform
