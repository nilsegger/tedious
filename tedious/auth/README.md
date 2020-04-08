# Authentication using [JWT Tokens](https://jwt.io/introduction/)
On sign in the user retrieves an access token. These tokens will consist of three parts: header, payload and signature, separated by dots.
The header and payload are key value constructs (json), encoded in base64.
The signature is created by encoding the header + payload with a private key, which has to be kept private.
The matching public key can be distributed to verify the token.

**Header should contain**
* 'typ': type of token, should be 'JWT'
* 'alg': algorithm used to encode signature
* 'kid': identifies key
* 'jwk': holds public json web key or a url pointing to a list of all valid keys
* 'x5c': public key in the format of an X509 or a url pointing to a list of all valid keys

**Payload should contain**
* 'exp': Expiration date
* 'nbf': Not before, datetime at which token becomes valid for use
* 'iss': Issuer of token
* 'aud': Audience, service for which token is meant to be used by
* 'iat': Time at which token was issued
* additional claims like role, name, uid

[JWT Cheat Sheet](https://pragmaticwebsecurity.com/img/cheatsheets/jwt.png)

## Authentication Flow
1. User signs in and retrieves a token. Created with a randomly selected token from directory.
2. User decodes payload, validates iss and exp. Custom claims like uid continue integration.
3. User requests profile data, sends token along, token gets verified using public key, public key is determined by kid
    iss, exp, nbf, aud is validated.

## Refresh tokens
To stop the platform from continuously asking the user to authenticate and limiting the lifespan of an access token,
refresh tokens are sent along on sign in.  
A refresh token is a random string which does not contain any information. When an access token dies, the user can send their refresh token
to the api and retrieve a fresh access token after their activity is checked for malicious actions.  
Refresh tokens have to be stored securely and there has to be the option of revoking refresh tokens.
