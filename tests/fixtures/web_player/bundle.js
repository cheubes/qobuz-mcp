// Synthetic excerpt reproducing only the patterns qobuz-mcp searches for. Values are fake.
var c={integration:{api:{appId:"111111111",appSecret:"fake-integration"}},production:{api:{appId:"123456789",appSecret:"fake-production"}}};
function login(n,t){return n.authenticate({privateKey:"fakePrivateKey",code:t})}
