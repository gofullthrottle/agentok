import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/supabase/server';

const NEXT_PUBLIC_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || 'https://localhost:5004';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const message = await request.json();

  console.log('post chat/input', id, message);

  try {
    const {
      data: { session },
    } = await getSession();
    if (!session || !session.access_token) {
      throw new Error('No session or access token found');
    }

    const res = await fetch(`${NEXT_PUBLIC_BACKEND_URL}/v1/chats/${id}/input`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify(message),
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error('Error', errorText);
      return NextResponse.json(
        { error: res.statusText },
        { status: res.status }
      );
    }

    const messages = await res.json();
    return NextResponse.json(messages);
  } catch (e) {
    console.error('Error', e);
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
