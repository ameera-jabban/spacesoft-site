/* Space Soft ERP subscription estimate engine (no DOM; shared by the pricing page and the tests).
 *
 *   SSPricing.estimate(config, input, options) -> result
 *
 * config   src/data/pricing.json (public price list)
 * input    { country: 'jo'|'ae'|'sy', cycle: 'annual'|'monthly', users, cashiers, reps, vans, restaurants, manufacturing }
 *            users        full-permission ERP accounts (limited cashier / rep logins are included in their unit)
 *            cashiers     extra POS cashier points (each restaurant branch already includes one)
 *            reps         independent sales reps (each cash van already includes one)
 *            vans, restaurants  counts; manufacturing  true/false (one company)
 * options  { launchEligible: bool, implementationFee: number|null }
 *            launchEligible     only when the launch offer was verified (trusted source); never assumed
 *            implementationFee  a scoped implementation price (quotes / tests). The public page leaves it null
 *                               and shows the "from" price outside the total.
 *
 * All money is handled in integer cents; each line is rounded to the cent.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.SSPricing = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const QTY_FIELDS = ['users', 'cashiers', 'reps', 'vans', 'restaurants'];

  class ValidationError extends Error {
    constructor(errors) { super('Invalid input: ' + errors.map(e => e.field).join(', ')); this.errors = errors; }
  }

  /** Returns [] when valid, else [{field, code}] — code: 'not_integer' | 'negative' | 'min_one' | 'unknown_country' | 'unknown_cycle'. */
  function validate(config, input) {
    const errors = [];
    if (!config.countries[input.country]) errors.push({ field: 'country', code: 'unknown_country' });
    if (input.cycle !== 'annual' && input.cycle !== 'monthly') errors.push({ field: 'cycle', code: 'unknown_cycle' });
    for (const f of QTY_FIELDS) {
      const v = input[f] === undefined ? 0 : input[f];
      if (typeof v !== 'number' || !Number.isFinite(v) || !Number.isInteger(v)) errors.push({ field: f, code: 'not_integer' });
      else if (v < 0) errors.push({ field: f, code: 'negative' });
      else if (f === 'users' && v < 1) errors.push({ field: f, code: 'min_one' });
    }
    if (input.manufacturing !== undefined && typeof input.manufacturing !== 'boolean') errors.push({ field: 'manufacturing', code: 'not_boolean' });
    return errors;
  }

  const cents = usd => Math.round(usd * 100);

  /** Annual price (USD) -> price per billing period in cents. */
  function periodCents(config, annualUsd, cycle) {
    const c = cents(annualUsd);
    return cycle === 'annual' ? c : Math.round(c / config.monthlyDivisor);
  }

  /** Cost of running `users` on each plan; picks the cheapest, ties go to the larger plan. */
  function choosePlan(config, list, users, cycle) {
    const eu = config.extraUsers;
    const plans = config.plans.slice().sort((a, b) => a.users - b.users);
    const largest = plans[plans.length - 1];
    const candidates = [];
    if (users > eu.maxUsersOnTiers) {
      const extra = users - largest.users;
      const unit = periodCents(config, eu.over15Annual[list], cycle);
      candidates.push({ plan: largest, extraUsers: extra, extraUnit: unit, tier: 'over15',
                        planCents: periodCents(config, largest.annual[list], cycle), extraCents: extra * unit });
    } else {
      for (const p of plans) {
        const extra = Math.max(0, users - p.users);
        const unit = periodCents(config, eu.upTo15Annual[list], cycle);
        candidates.push({ plan: p, extraUsers: extra, extraUnit: unit, tier: 'upTo15',
                          planCents: periodCents(config, p.annual[list], cycle), extraCents: extra * unit });
      }
    }
    candidates.forEach(c => { c.totalCents = c.planCents + c.extraCents; });
    let best = candidates[0];
    for (const c of candidates) {
      if (c.totalCents < best.totalCents || (c.totalCents === best.totalCents && c.plan.users > best.plan.users)) best = c;
    }
    return { best, candidates };
  }

  function estimate(config, rawInput, options) {
    const opt = Object.assign({ launchEligible: false, implementationFee: null }, options || {});
    const input = Object.assign({ users: 1, cashiers: 0, reps: 0, vans: 0, restaurants: 0, manufacturing: false }, rawInput);
    const errors = validate(config, input);
    if (errors.length) throw new ValidationError(errors);

    const list = config.countries[input.country].list;
    const cycle = input.cycle;
    const { best, candidates } = choosePlan(config, list, input.users, cycle);

    const qty = { cashiers: input.cashiers, reps: input.reps, vans: input.vans, restaurants: input.restaurants,
                  manufacturing: input.manufacturing ? 1 : 0 };
    const addons = [], activation = [];
    for (const a of config.addons) {
      const q = qty[a.input] || 0;
      if (!q) continue;
      const unit = periodCents(config, a.annual[list], cycle);
      addons.push({ id: a.id, qty: q, unitCents: unit, totalCents: q * unit });
      if (a.activation) {
        const confirmed = a.activation.unit === 'perVan' || a.activation.unit === 'perSubscription';
        const aq = a.activation.unit === 'perSubscription' ? 1 : q;
        const unitAct = cents(a.activation.price[list]);
        activation.push({ id: a.id, qty: aq, unitCents: unitAct, totalCents: aq * unitAct, confirmed, unit: a.activation.unit });
      }
    }

    const subscriptionCents = best.planCents + best.extraCents;           // plan + extra users
    const addonsCents = addons.reduce((s, a) => s + a.totalCents, 0);
    const recurringCents = subscriptionCents + addonsCents;

    // Launch offer: annual subscription + recurring add-ons, first year only, never on one-time fees.
    let discount = null;
    const promo = config.launchPromo || {};
    if (opt.launchEligible && cycle === 'annual' && promo.percent) {
      const amount = Math.round(recurringCents * promo.percent / 100);
      discount = { type: 'launch', percent: promo.percent, amountCents: amount };
    }
    const recurringAfterCents = recurringCents - (discount ? discount.amountCents : 0);

    const activationConfirmedCents = activation.filter(a => a.confirmed).reduce((s, a) => s + a.totalCents, 0);
    const implementationFromCents = cents(config.implementationFrom[list]);
    const implementationCents = opt.implementationFee == null ? null : cents(opt.implementationFee);

    // First billing period (first year, or first month) = recurring after discount + confirmed one-time fees
    // (+ implementation only when a scoped amount is given).
    const firstPeriodCents = recurringAfterCents + activationConfirmedCents + (implementationCents || 0);
    const months = config.monthlyCommitmentMonths;

    return {
      country: input.country, list, cycle,
      users: input.users,
      plan: { id: best.plan.id, includedUsers: best.plan.users, priceCents: best.planCents },
      extraUsers: { count: best.extraUsers, unitCents: best.extraUnit, totalCents: best.extraCents, tier: best.tier },
      planComparison: candidates.map(c => ({ id: c.plan.id, totalCents: c.totalCents })),
      addons,
      recurringCents,
      discount,
      recurringAfterDiscountCents: recurringAfterCents,
      activation,
      activationIncludedCents: activationConfirmedCents,
      implementation: { fromCents: implementationFromCents, amountCents: implementationCents, includedInTotal: implementationCents != null },
      firstPeriodCents,
      renewalCents: recurringCents,                                         // renewal never carries the launch discount
      commitment: cycle === 'monthly' ? { months, recurringCents: recurringCents * months } : null,
    };
  }

  return { estimate, validate, choosePlan, ValidationError, version: 1 };
}));
