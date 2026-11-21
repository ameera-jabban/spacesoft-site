// Acceptance tests for the pricing engine (amounts before tax).  Run: node --test tools/tests/
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

const ROOT = path.join(__dirname, '..', '..');
const { estimate, validate, ValidationError } = require(path.join(ROOT, 'assets/js/pricing-engine.js'));
const BASE = JSON.parse(fs.readFileSync(path.join(ROOT, 'src/data/pricing.json'), 'utf8'));
const cfg = (patch = {}) => Object.assign(JSON.parse(JSON.stringify(BASE)), patch);
const usd = c => c / 100;
const annual = (country, users, extra = {}, opts) => estimate(cfg(), { country, cycle: 'annual', users, ...extra }, opts);

test('Jordan, 5 users, annual = $420 on Starter (300 + 2 extra users x 60)', () => {
  const r = annual('jo', 5);
  assert.equal(r.plan.id, 'starter');
  assert.equal(r.extraUsers.count, 2);
  assert.equal(usd(r.firstPeriodCents), 420);
});

test('Jordan, 8 / 15 / 16 users, annual = $600 / $1,000 / $1,050', () => {
  const r8 = annual('jo', 8), r15 = annual('jo', 15), r16 = annual('jo', 16);
  assert.equal(usd(r8.firstPeriodCents), 600);
  assert.equal(usd(r15.firstPeriodCents), 1000);
  assert.equal(r15.plan.id, 'pro');
  assert.equal(usd(r16.firstPeriodCents), 1050);
  assert.equal(r16.plan.id, 'pro');
  assert.equal(r16.extraUsers.tier, 'over15');
});

test('ties go to the larger plan (8 users: Starter+5 = Business = $600 -> Business)', () => {
  const r = annual('jo', 8);
  const starter = r.planComparison.find(p => p.id === 'starter'), business = r.planComparison.find(p => p.id === 'business');
  assert.equal(starter.totalCents, business.totalCents);
  assert.equal(r.plan.id, 'business');
});

test('Jordan, 3 users + 1 POS, launch offer + $300 implementation = $620 first year, $400 renewal', () => {
  const r = annual('jo', 3, { cashiers: 1 }, { launchEligible: true, implementationFee: 300 });
  assert.equal(r.plan.id, 'starter');
  assert.equal(usd(r.recurringCents), 400);
  assert.equal(usd(r.discount.amountCents), 80);
  assert.equal(usd(r.firstPeriodCents), 620);          // (300 + 100) x 80% + 300
  assert.equal(usd(r.renewalCents), 400);              // renewal without the launch discount
});

test('Syria, 4 users + 2 restaurant branches, annual = $780 (200 + 40 + 2 x 270), one cashier per branch included', () => {
  const r = annual('sy', 4, { restaurants: 2 });
  assert.equal(r.plan.id, 'starter');
  assert.equal(usd(r.firstPeriodCents), 780);
  assert.equal(r.addons.find(a => a.id === 'pos'), undefined, 'no POS charge for the cashier included with each branch');
});

test('Syria uses its own list, not a percentage of the Jordan/UAE prices', () => {
  assert.equal(usd(annual('sy', 15).firstPeriodCents), 670);
  assert.equal(usd(annual('sy', 16).firstPeriodCents), 705);   // 670 + 35
  assert.equal(usd(annual('ae', 15).firstPeriodCents), 1000);   // UAE shares the Jordan list
});

test('launch offer is never applied without verified eligibility, nor to monthly billing', () => {
  assert.equal(annual('jo', 3, { cashiers: 1 }).discount, null);
  const m = estimate(cfg(), { country: 'jo', cycle: 'monthly', users: 3, cashiers: 1 }, { launchEligible: true });
  assert.equal(m.discount, null);
});

test('discount excludes implementation and activation', () => {
  const c = cfg(); c.addons.find(a => a.id === 'van').activation.unit = 'perVan';
  const r = estimate(c, { country: 'jo', cycle: 'annual', users: 3, vans: 1 }, { launchEligible: true, implementationFee: 300 });
  // recurring 300 + 100 = 400 -> 320 after 20%; + van activation 50 + implementation 300
  assert.equal(usd(r.discount.amountCents), 80);
  assert.equal(usd(r.firstPeriodCents), 670);
});

test('monthly = annual / 10 for every recurring item, with a 3-month initial commitment', () => {
  const r = estimate(cfg(), { country: 'jo', cycle: 'monthly', users: 5, reps: 2, manufacturing: true });
  assert.equal(usd(r.plan.priceCents), 30);
  assert.equal(usd(r.extraUsers.unitCents), 6);
  assert.equal(usd(r.addons.find(a => a.id === 'reps').unitCents), 3);
  assert.equal(usd(r.addons.find(a => a.id === 'manufacturing').totalCents), 50);
  assert.equal(usd(r.recurringCents), 30 + 12 + 6 + 50);
  assert.deepEqual(r.commitment, { months: 3, recurringCents: (30 + 12 + 6 + 50) * 300 });
  const sy = estimate(cfg(), { country: 'sy', cycle: 'monthly', users: 15 });
  assert.equal(usd(sy.firstPeriodCents), 67);                  // Pro, Syria: 670 / 10
});

test('cash van includes one rep; only independent reps are charged', () => {
  const r = annual('jo', 3, { vans: 2, reps: 1 });
  assert.equal(usd(r.addons.find(a => a.id === 'van').totalCents), 200);
  assert.equal(usd(r.addons.find(a => a.id === 'reps').totalCents), 30);
});

test('manufacturing is a separate line, independent of plan and users', () => {
  const a = annual('jo', 3, { manufacturing: true }), b = annual('jo', 15, { manufacturing: true });
  assert.equal(usd(a.addons.find(x => x.id === 'manufacturing').totalCents), 500);
  assert.equal(usd(b.addons.find(x => x.id === 'manufacturing').totalCents), 500);
  assert.equal(a.plan.id, 'starter');
});

test('cash-van activation: unapproved unit stays out of the total; once approved it is charged once and not on renewal', () => {
  const pending = annual('jo', 3, { vans: 3 });
  assert.equal(pending.activation[0].confirmed, false);
  assert.equal(pending.activationIncludedCents, 0);
  assert.equal(usd(pending.firstPeriodCents), 600);           // 300 + 3 x 100

  const c = cfg(); c.addons.find(a => a.id === 'van').activation.unit = 'perSubscription';
  const once = estimate(c, { country: 'jo', cycle: 'annual', users: 3, vans: 3 });
  assert.equal(once.activation[0].qty, 1);
  assert.equal(usd(once.firstPeriodCents), 650);
  assert.equal(usd(once.renewalCents), 600);

  c.addons.find(a => a.id === 'van').activation.unit = 'perVan';
  const perVan = estimate(c, { country: 'sy', cycle: 'annual', users: 3, vans: 3 });
  assert.equal(usd(perVan.activationIncludedCents), 105);       // 3 x 35
});

test('implementation is shown as a "from" price and is not in the public total', () => {
  const r = annual('jo', 3);
  assert.equal(usd(r.implementation.fromCents), 300);
  assert.equal(r.implementation.includedInTotal, false);
  assert.equal(usd(annual('sy', 3).implementation.fromCents), 100);
});

test('changing country, cycle or quantities changes the estimate', () => {
  const base = annual('jo', 5);
  assert.notEqual(annual('sy', 5).firstPeriodCents, base.firstPeriodCents);
  assert.notEqual(estimate(cfg(), { country: 'jo', cycle: 'monthly', users: 5 }).firstPeriodCents, base.firstPeriodCents);
  assert.notEqual(annual('jo', 6).firstPeriodCents, base.firstPeriodCents);
  assert.notEqual(annual('jo', 5, { reps: 1 }).firstPeriodCents, base.firstPeriodCents);
});

test('negative and fractional quantities are rejected', () => {
  for (const bad of [{ users: -1 }, { users: 2.5 }, { users: 0 }, { cashiers: -2 }, { reps: 1.5 }, { vans: NaN }, { restaurants: '2' }]) {
    assert.throws(() => estimate(cfg(), { country: 'jo', cycle: 'annual', users: 3, ...bad }), ValidationError, JSON.stringify(bad));
  }
  assert.deepEqual(validate(cfg(), { country: 'xx', cycle: 'weekly', users: 1 }).map(e => e.field), ['country', 'cycle']);
});

test('amounts are exact to the cent', () => {
  const r = estimate(cfg(), { country: 'sy', cycle: 'monthly', users: 16 });
  assert.equal(r.firstPeriodCents, 6700 + 350);                // 67 + 3.50
});

test('the public price list carries no internal commercial data', () => {
  const text = JSON.stringify(BASE).toLowerCase();
  for (const word of ['commission', 'agent', 'reseller', 'hr_price', '807', '7.5', 'approval']) {
    assert.ok(!text.includes(word), `pricing.json must not contain "${word}"`);
  }
});
