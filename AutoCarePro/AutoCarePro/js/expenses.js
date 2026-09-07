/* ==========================================================================
   AutoCare Pro — expenses.js
   Expense CRUD plus the aggregations the Expenses and Analytics pages read.
   All money is stored as a plain number of rupees; formatting happens in the
   view layer only.
   ========================================================================== */

window.AC = window.AC || {};

AC.expenses = (function () {
  "use strict";

  const U = AC.utils;
  const C = AC.constants;
  const S = AC.storage;

  const all = () => U.sortBy(S.list("expenses"), (e) => e.date, "desc");

  /** Filter helper shared by every aggregation below. */
  function query({ vehicleId = null, category = null, from = null, to = null } = {}) {
    return all().filter((e) => {
      if (vehicleId && e.vehicleId !== vehicleId) return false;
      if (category && e.category !== category) return false;
      if (from && e.date < from) return false;
      if (to && e.date > to) return false;
      return true;
    });
  }

  const total = (filter = {}) => U.sum(query(filter), (e) => e.amount);

  /** Spend for the current calendar month. */
  function monthToDate(filter = {}) {
    const now = U.today();
    const first = U.isoDate(new Date(now.getFullYear(), now.getMonth(), 1));
    return total({ ...filter, from: first });
  }

  /** Totals per category, largest first, with share of the whole. */
  function byCategory(filter = {}) {
    const rows = query(filter);
    const grand = U.sum(rows, (e) => e.amount) || 1;
    return C.EXPENSE_CATEGORIES.map((cat) => {
      const amount = U.sum(
        rows.filter((e) => e.category === cat.key),
        (e) => e.amount
      );
      return { ...cat, amount, share: amount / grand };
    })
      .filter((c) => c.amount > 0)
      .sort((a, b) => b.amount - a.amount);
  }

  /** Month-by-month totals for the trailing `months` window. */
  function monthly(filter = {}, months = 6) {
    const rows = query(filter);
    const buckets = new Map();
    for (let i = months - 1; i >= 0; i -= 1) {
      buckets.set(U.formatMonthKey(U.addMonths(U.today(), -i)), 0);
    }
    rows.forEach((e) => {
      const key = U.formatMonthKey(e.date);
      if (buckets.has(key)) buckets.set(key, buckets.get(key) + Number(e.amount));
    });
    return Array.from(buckets.entries()).map(([key, value]) => ({
      key,
      label: U.monthLabel(key),
      value,
    }));
  }

  /** Stacked monthly series split by category — used by the analytics page. */
  function monthlyByCategory(filter = {}, months = 6) {
    const labels = monthly(filter, months).map((m) => m.label);
    const keys = monthly(filter, months).map((m) => m.key);
    const series = C.EXPENSE_CATEGORIES.map((cat) => {
      const data = keys.map((key) =>
        U.sum(
          query({ ...filter, category: cat.key }).filter((e) => U.formatMonthKey(e.date) === key),
          (e) => e.amount
        )
      );
      return { ...cat, data };
    }).filter((s) => s.data.some((v) => v > 0));
    return { labels, series };
  }

  const create = (value) =>
    S.insert("expenses", {
      vehicleId: value.vehicleId,
      category: value.category,
      amount: Number(value.amount),
      date: value.date,
      description: value.description || "",
      source: "user",
    });

  const update = (id, value) =>
    S.patch("expenses", id, {
      vehicleId: value.vehicleId,
      category: value.category,
      amount: Number(value.amount),
      date: value.date,
      description: value.description || "",
    });

  const remove = (id) => S.remove("expenses", id);

  /** Cost per kilometre — a genuinely useful ownership metric. */
  function costPerKm(vehicleId) {
    const vehicle = AC.vehicles.get(vehicleId);
    if (!vehicle) return null;
    const spent = total({ vehicleId });
    const journeyKm = AC.journeys.forVehicle(vehicleId).reduce((a, j) => a + Number(j.distanceKm), 0);
    const basis = journeyKm > 100 ? journeyKm : Number(vehicle.odometer) || 0;
    if (!basis) return null;
    return spent / basis;
  }

  return {
    all,
    query,
    total,
    monthToDate,
    byCategory,
    monthly,
    monthlyByCategory,
    create,
    update,
    remove,
    costPerKm,
  };
})();
