import { NextResponse } from "next/server";
import { getAdminAuthError } from "@/lib/admin-auth";
import {
  saveCharacterExtended,
  readCharacterExtended,
  readAllCharacterExtended,
  saveRelationships,
  readRelationships,
  saveCollections,
  readCollections,
  saveWorlds,
  readWorlds,
  savePlaces,
  readPlaces,
  saveLorebooks,
  readLorebooks,
  saveAssets,
  readAssets,
  appendAuditLog,
} from "@/lib/admin-store";
import type { Place, LorebookEntry, WorldData, Asset } from "@/lib/admin-store";

export const runtime = "nodejs";

const audit = (cat: "character"|"world"|"prompt"|"ai"|"memory"|"operation", action: string, target: string) =>
  appendAuditLog({ category: cat, action, target, adminUser: "admin" }).catch(() => {});

export async function POST(request: Request) {
  const authError = getAdminAuthError(request);
  if (authError) return authError;

  const body = await request.json() as Record<string, unknown>;
  const action = body.action as string;

  try {
    switch (action) {
      case "saveCharacterExtended":
        return NextResponse.json({ characterExtended: await saveCharacterExtended(body.characterId as string, body.data as Record<string, unknown>) });

      case "getCharacterExtended":
        return NextResponse.json({ characterExtended: await readCharacterExtended(body.characterId as string), all: await readAllCharacterExtended() });

      case "saveRelationship": {
        let rels = await readRelationships();
        const r = body.data as Record<string, unknown>;
        const idx = r.id ? rels.findIndex((x) => x.id === r.id) : -1;
        if (idx >= 0) rels[idx] = { ...rels[idx], relation: (r.relation as string) ?? rels[idx].relation, description: (r.description as string) ?? rels[idx].description, events: (r.events as string) ?? rels[idx].events, secrets: (r.secrets as string) ?? rels[idx].secrets } as typeof rels[0];
        else rels.push({ id: crypto.randomUUID(), fromCharacterId: r.fromCharacterId ?? "", toCharacterId: r.toCharacterId ?? "", relation: r.relation ?? "", description: r.description ?? "", events: r.events ?? "", secrets: r.secrets ?? "", createdAt: new Date().toISOString() } as typeof rels[0]);
        rels = await saveRelationships(rels);
        await audit("character", "relationship_updated", (r.fromCharacterId ?? "") as string);
        return NextResponse.json({ relationships: rels });
      }
      case "deleteRelationship": {
        let rels = await readRelationships();
        rels = await saveRelationships(rels.filter((r) => r.id !== (body.id as string)));
        return NextResponse.json({ relationships: rels });
      }
      case "getRelationships":
        return NextResponse.json({ relationships: await readRelationships() });

      case "saveCollection": {
        let colls = await readCollections();
        const c = body.data as Record<string, unknown>;
        const idx = c.id ? colls.findIndex((x) => x.id === c.id) : -1;
        if (idx >= 0) colls[idx] = { ...colls[idx], title: (c.title as string) ?? colls[idx].title, description: (c.description as string) ?? colls[idx].description, characterIds: (c.characterIds as string[]) ?? colls[idx].characterIds, sortOrder: (c.sortOrder as number) ?? colls[idx].sortOrder, isPublic: (c.isPublic as boolean) ?? colls[idx].isPublic } as typeof colls[0];
        else colls.push({ id: crypto.randomUUID(), title: c.title ?? "", description: c.description ?? "", characterIds: (c.characterIds as string[]) ?? [], sortOrder: (c.sortOrder as number) ?? 0, isPublic: (c.isPublic as boolean) ?? false, createdAt: new Date().toISOString() } as typeof colls[0]);
        colls = await saveCollections(colls);
        await audit("character", "collection_updated", (c.title ?? "") as string);
        return NextResponse.json({ collections: colls });
      }
      case "deleteCollection": {
        let colls = await readCollections();
        colls = await saveCollections(colls.filter((c) => c.id !== (body.id as string)));
        return NextResponse.json({ collections: colls });
      }
      case "getCollections":
        return NextResponse.json({ collections: await readCollections() });

      case "saveWorld": {
        let worlds = await readWorlds();
        const w = body.data as Record<string, unknown>;
        const idx = w.id ? worlds.findIndex((x) => x.id === w.id) : -1;
        const now = new Date().toISOString();
        if (idx >= 0) worlds[idx] = { ...worlds[idx], name: (w.name as string) ?? worlds[idx].name, overview: (w.overview as string) ?? worlds[idx].overview, updatedAt: now } as WorldData;
        else worlds.push({ id: crypto.randomUUID(), name: w.name ?? "", overview: "", locations: "", organizations: "", characters: "", history: "", events: "", rules: "", terms: "", createdAt: now, updatedAt: now } as typeof worlds[0]);
        worlds = await saveWorlds(worlds);
        await audit("world", "world_updated", (w.name ?? "") as string);
        return NextResponse.json({ worlds });
      }
      case "deleteWorld": {
        let worlds = await readWorlds();
        worlds = await saveWorlds(worlds.filter((w) => w.id !== (body.id as string)));
        return NextResponse.json({ worlds });
      }
      case "getWorlds":
        return NextResponse.json({ worlds: await readWorlds() });

      case "savePlace": {
        let places = await readPlaces();
        const p = body.data as Record<string, unknown>;
        const idx = p.id ? places.findIndex((x) => x.id === p.id) : -1;
        if (idx >= 0) places[idx] = { ...places[idx], name: (p.name as string) ?? places[idx].name, description: (p.description as string) ?? places[idx].description, atmosphere: (p.atmosphere as string) ?? places[idx].atmosphere } as Place;
        else places.push({ id: crypto.randomUUID(), name: (p.name as string) ?? "", description: "", atmosphere: "", relatedCharacterIds: [], relatedSceneIds: [], relatedLorebookIds: [], createdAt: new Date().toISOString() } as Place);
        places = await savePlaces(places);
        await audit("world", "place_updated", (p.name ?? "") as string);
        return NextResponse.json({ places });
      }
      case "deletePlace": {
        let places = await readPlaces();
        places = await savePlaces(places.filter((p) => p.id !== (body.id as string)));
        return NextResponse.json({ places });
      }
      case "getPlaces":
        return NextResponse.json({ places: await readPlaces() });

      case "saveLorebook": {
        let lbs = await readLorebooks();
        const lb = body.data as Record<string, unknown>;
        const idx = lb.id ? lbs.findIndex((x) => x.id === lb.id) : -1;
        if (idx >= 0) lbs[idx] = { ...lbs[idx], name: (lb.name as string) ?? lbs[idx].name, keywords: (lb.keywords as string[]) ?? lbs[idx].keywords, content: (lb.content as string) ?? lbs[idx].content, priority: (lb.priority as number) ?? lbs[idx].priority, isActive: (lb.isActive as boolean) ?? lbs[idx].isActive } as LorebookEntry;
        else lbs.push({ id: crypto.randomUUID(), name: (lb.name as string) ?? "", keywords: (lb.keywords as string[]) ?? [], content: (lb.content as string) ?? "", characterIds: [], worldId: undefined, priority: (lb.priority as number) ?? 0, isActive: true, createdAt: new Date().toISOString() } as LorebookEntry);
        lbs = await saveLorebooks(lbs);
        await audit("world", "lorebook_updated", (lb.name ?? "") as string);
        return NextResponse.json({ lorebooks: lbs });
      }
      case "deleteLorebook": {
        let lbs = await readLorebooks();
        lbs = await saveLorebooks(lbs.filter((l) => l.id !== (body.id as string)));
        return NextResponse.json({ lorebooks: lbs });
      }
      case "getLorebooks":
        return NextResponse.json({ lorebooks: await readLorebooks() });

      case "saveAsset": {
        let assets = await readAssets();
        const a = body.data as Record<string, unknown>;
        const idx = a.id ? assets.findIndex((x) => x.id === a.id) : -1;
        if (idx >= 0) assets[idx] = { ...assets[idx], name: (a.name as string) ?? assets[idx].name, type: (a.type as "other") ?? assets[idx].type, url: (a.url as string) ?? assets[idx].url } as Asset;
        else assets.push({ id: crypto.randomUUID(), name: (a.name as string) ?? "", type: (a.type as Asset["type"]) ?? "other", url: (a.url as string) ?? "", usedBy: [], createdAt: new Date().toISOString() } as Asset);
        assets = await saveAssets(assets);
        return NextResponse.json({ assets });
      }
      case "deleteAsset": {
        let assets = await readAssets();
        const asset = assets.find((a) => a.id === (body.id as string));
        if (asset?.usedBy.length) return NextResponse.json({ error: `사용 중인 에셋은 삭제할 수 없습니다. 사용 위치: ${asset.usedBy.join(", ")}` }, { status: 400 });
        assets = await saveAssets(assets.filter((a) => a.id !== (body.id as string)));
        return NextResponse.json({ assets });
      }
      case "getAssets":
        return NextResponse.json({ assets: await readAssets() });

      case "getAllCharacterExtended":
        return NextResponse.json({ allExtended: await readAllCharacterExtended() });

      default:
        return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
    }
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
