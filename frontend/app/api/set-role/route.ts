import { auth, clerkClient } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json();
  const role: string = body?.role;

  if (role !== "admin" && role !== "user") {
    return NextResponse.json({ error: "Invalid role" }, { status: 400 });
  }

  const client = await clerkClient();
  await client.users.updateUser(userId, {
    publicMetadata: { role },
  });

  return NextResponse.json({ success: true });
}
