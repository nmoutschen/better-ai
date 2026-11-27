# 3-D Secure 2 rollout review

Author: Jonas Weber
Date: 2026-03-28

Since release 26.3, the share of card payments that get a 3-D Secure challenge rose from 8% to 31%.

40% of customers who get a challenge abandon checkout at that step.

Most of the abandonment increase happened at the challenge step.

The provider's default risk threshold was left in place; their documentation recommends tuning it for each merchant.

We recommend lowering the challenge rate by tuning the threshold, not switching 3-D Secure 2 off, because the card schemes require it from 2026-06-01.

The provider also offers network tokens for cards that customers store with us. The payments team plans to evaluate them in the third quarter.
