const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type' } };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method not allowed' };
  }

  try {
    const { plan, company, username, userId } = JSON.parse(event.body);

    const prices = {
      crew: { amount: 9900, name: 'REVV Crew Plan', interval: 'month' },
      company: { amount: 29900, name: 'REVV Company Plan', interval: 'month' },
    };

    const selected = prices[plan];
    if (!selected) {
      return { statusCode: 400, body: JSON.stringify({ error: 'Invalid plan' }) };
    }

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      mode: 'subscription',
      line_items: [{
        price_data: {
          currency: 'usd',
          product_data: { name: selected.name, description: 'REVV â€” ' + selected.name + ' for ' + (company || 'your company') },
          recurring: { interval: selected.interval },
          unit_amount: selected.amount,
        },
        quantity: 1,
      }],
      metadata: { plan, company: company || '', username: username || '', userId: userId || '' },
      success_url: event.headers.origin + '/demo.html?payment=success&plan=' + plan,
      cancel_url: event.headers.origin + '/signup.html?payment=cancelled',
      allow_promotion_codes: true,
    });

    return {
      statusCode: 200,
      headers: { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: session.url, sessionId: session.id }),
    };
  } catch (err) {
    return {
      statusCode: 500,
      headers: { 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ error: err.message }),
    };
  }
};
