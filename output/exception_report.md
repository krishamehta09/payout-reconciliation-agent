# Payout Reconciliation Exception Report

Mode: rules + Gemini triage  
Exceptions flagged: **15**  
Net dollar variance: **$16,412.00**  
Validation vs. seeded errors: caught 15/15 (recall 100%), precision 100%

| Deal | Rep | Type | Severity | Variance | Action |
|---|---|---|---|---:|---|
| D-1074 | Quinn Murphy | duplicate | high | $7,575.00 | Void the duplicate payout P-9000 and claw back the overpaid $7,575.00. |
| D-1103 | Jordan Patel | duplicate | high | $6,975.00 | Void the duplicate payout P-9002 and claw back the overpaid $6,975.00. |
| D-1106 | Sam Rivera | missing_credit | high | $-4,350.00 | Manually credit the closed deal and release the expected $4,350.00 payout. |
| D-1195 | Parker Singh | duplicate | high | $3,700.00 | Void the duplicate payout P-9003 and claw back the overpaid $3,700.00. |
| D-1042 | Quinn Murphy | wrong_rate | high | $2,440.00 | Adjust the commission rate to 8% and claw back the $2,440.00 overpayment in the next pay cycle. |
| D-1170 | Drew Kim | duplicate | high | $2,360.00 | Void the duplicate payout P-9001 and claw back the overpaid $2,360.00. |
| D-1178 | Jamie Foster | missing_credit | medium | $-1,590.00 | Manually credit the closed deal and release the expected $1,590.00 payout. |
| D-1027 | Casey Diaz | wrong_rate | medium | $1,085.00 | Adjust the commission rate to 10% and claw back the $1,085.00 overpayment in the next pay cycle. |
| D-1127 | Sam Rivera | missing_credit | medium | $-1,040.00 | Manually credit the closed deal and release the expected $1,040.00 payout. |
| D-1010 | Blake Torres | amount_mismatch | medium | $-823.00 | Process a retroactive payment of $823.00 to correct the underpayment. |
| D-1085 | Morgan Lee | missing_credit | medium | $-800.00 | Manually credit the closed deal and release the expected $800.00 payout. |
| D-1172 | Jordan Patel | wrong_rate | medium | $680.00 | Adjust the commission rate to 10% and claw back the $680.00 overpayment in the next pay cycle. |
| D-1117 | Jordan Patel | amount_mismatch | medium | $573.00 | Recalculate the payout based on the correct rate and claw back the $573.00 overpayment. |
| D-1141 | Riley Nguyen | amount_mismatch | medium | $-563.00 | Process a retroactive payment of $563.00 to correct the underpayment. |
| D-1083 | Blake Torres | wrong_rate | low | $190.00 | Adjust the commission rate to 8% and claw back the $190.00 overpayment in the next pay cycle. |