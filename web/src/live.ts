// PC 프로그램 실시간 알림 (Durable Object + 웹소켓)
// - 로그인한 PC 프로그램은 켜져 있는 동안 /api/live 로 연결해 둔다 (회원마다 알림 통로 1개)
// - 유료 여부 · 기기 해제 · 회원 정지가 바뀌면 notifyUser() 가 그 회원의 모든 PC 에 바로 알린다
// - 알림을 받은 프로그램은 /api/me 를 다시 불러 광고를 끄거나 켠다
// - 연결이 조용할 때는 잠들어 있어서(hibernation) 비용이 거의 들지 않고,
//   프로그램이 보내는 "ping" 은 깨우지 않고 "pong" 으로 자동 응답한다
import { DurableObject } from "cloudflare:workers";
import type { Env } from "./db";

export class LiveHub extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair("ping", "pong"));
  }

  async fetch(req: Request): Promise<Response> {
    if (new URL(req.url).pathname === "/notify") {
      const msg = await req.text();
      let sent = 0;
      for (const ws of this.ctx.getWebSockets()) {
        try { ws.send(msg); sent++; } catch { /* 이미 끊긴 연결 */ }
      }
      return Response.json({ sent });
    }
    if (req.headers.get("Upgrade") !== "websocket") return new Response("websocket only", { status: 426 });
    const pair = new WebSocketPair();
    this.ctx.acceptWebSocket(pair[1]);
    return new Response(null, { status: 101, webSocket: pair[0] });
  }

  async webSocketMessage() { /* 프로그램이 보내는 내용은 ping 뿐이라 따로 처리할 것이 없다 */ }

  async webSocketClose(ws: WebSocket, code: number) {
    try { ws.close(code === 1005 ? 1000 : code, "bye"); } catch { /* 이미 닫힘 */ }
  }
}

const hub = (env: Env, userId: number) => env.LIVE.get(env.LIVE.idFromName(`user:${userId}`));

/** PC 프로그램의 실시간 연결을 그 회원의 알림 통로로 넘긴다 */
export const connectLive = (env: Env, userId: number, req: Request) => hub(env, userId).fetch(req);

/** 이 회원의 켜져 있는 PC 프로그램 모두에게 "계정 상태가 바뀌었어요" 알림 (실패해도 원래 작업은 계속) */
export async function notifyUser(env: Env, userId: number) {
  try {
    await hub(env, userId).fetch("https://live/notify", { method: "POST", body: JSON.stringify({ type: "account" }) });
  } catch (e) {
    console.log("live notify failed", userId, String(e));
  }
}
