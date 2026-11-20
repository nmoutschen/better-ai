# Q4 forecast: working notes

For Lena Haddad (CFO). She uses the Q4 forecast to set the Q1 hiring plan at the leadership meeting on 2 December.

## Method

- Base case = weighted open pipeline: amount x stage probability, summed over every open deal.
- Data: sources/pipeline.csv (CRM export, 18 November). Sum of weighted_eur = EUR 1,420,000.
- Stage probabilities: discovery 20%, proposal 50%, negotiation 80%, commit 90%. Same as last year's model.
- Range: EUR 1.25M (low) to EUR 1.55M (high), using the lowest and highest quarterly win rates of the last four quarters.
- Tried a regression on eight quarters of history first. Too noisy with this few data points, dropped it.

## Comparison with Q3

- Q3 actual per the CRM dashboard: EUR 1.31M.
- Q3 not reconciled. Finance's booked-revenue export for Q3 was not in the shared drive, so the CRM figure is unconfirmed. In earlier quarters CRM and booked revenue differed by 2-4%.
- Q4 base case vs Q3: +8%. Depends on the Q3 figure being right.

## Concentration

- Halden Foods (EUR 400k, negotiation) and Mwangi Logistics (EUR 250k, negotiation) make up EUR 520k of the weighted total, 37%.
- If either of them slips to Q1, Q4 falls below the low end of the range.

## Open

- Ask finance for the Q3 export again on Monday.
