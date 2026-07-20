// urth. — Supabase Edge Function: send a Web Push notification when an
// order's status changes to a "key stage" (ready / dispatched / cancelled).
//
// Triggered by a Supabase Database Webhook on orders (UPDATE), configured
// in the dashboard (see README below / the setup doc). Not called directly
// by the client app.
//
// Secrets required (set via `supabase secrets set`, see setup doc):
//   VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT (mailto: address)
// SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are provided automatically to
// every Edge Function — no need to set them yourself.

import webpush from "npm:web-push@3.6.7";
import { createClient } from "npm:@supabase/supabase-js@2.110.7";

const NOTIFY_LABEL: Record<string, string> = {
  ready: "Ready",
  dispatched: "Dispatched",
  cancelled: "Cancelled",
};

webpush.setVapidDetails(
  Deno.env.get("VAPID_SUBJECT") ?? "mailto:owner@example.com",
  Deno.env.get("VAPID_PUBLIC_KEY")!,
  Deno.env.get("VAPID_PRIVATE_KEY")!,
);

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

Deno.serve(async (req) => {
  try {
    const payload = await req.json();
    // Supabase DB Webhook payload shape: { type, table, record, old_record, ... }
    const rec = payload.record ?? payload.new;
    const old = payload.old_record ?? payload.old;
    if (!rec) return new Response("no record", { status: 200 });

    const status = rec.status as string;
    const label = NOTIFY_LABEL[status];
    // Only notify on an actual change into a key stage.
    if (!label || (old && old.status === status)) {
      return new Response("skip", { status: 200 });
    }

    const { data: subs, error } = await supabase
      .from("push_subscriptions")
      .select("endpoint,p256dh,auth");
    if (error) throw error;
    if (!subs || subs.length === 0) return new Response("no subscribers", { status: 200 });

    const title = `urth · ${rec.order_no || "Order"} — ${label}`;
    const bodyParts = [rec.customer_name || ""];
    if (status === "dispatched" && rec.address) bodyParts.push(rec.address);
    const body = bodyParts.filter(Boolean).join(" · ");
    const payloadStr = JSON.stringify({ title, body, tag: `order-${rec.id}`, url: "/" });

    const results = await Promise.allSettled(
      subs.map((s) =>
        webpush.sendNotification(
          { endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } },
          payloadStr,
        )
      ),
    );

    // Clean up subscriptions the browser has revoked/expired (410/404).
    const dead: string[] = [];
    results.forEach((r, i) => {
      if (r.status === "rejected") {
        const code = (r.reason && (r.reason.statusCode || r.reason.status)) || 0;
        if (code === 410 || code === 404) dead.push(subs[i].endpoint);
      }
    });
    if (dead.length) {
      await supabase.from("push_subscriptions").delete().in("endpoint", dead);
    }

    return new Response(JSON.stringify({ sent: subs.length - dead.length, pruned: dead.length }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error(e);
    return new Response(String(e), { status: 500 });
  }
});
