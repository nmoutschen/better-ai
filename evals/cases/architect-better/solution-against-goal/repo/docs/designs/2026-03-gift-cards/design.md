# Design: gift cards

Status: approved March 2026; postponed, not built yet

## Goal

Customers can buy a gift card and pay an order with it.

## Design

- New table `gift_cards` (code, balance_cents, created_at) in the SQLite file.
- `POST /v1/gift-cards` buys one (paid through PayLane like an order); the code is emailed through the outbox.
- At checkout, a gift card code reduces the amount charged through PayLane.

## Decisions

- Codes are 16 random characters from `secrets.token_urlsafe`; no expiry (Belgian law sets a minimum of one year; we
  chose none to keep it simple).
