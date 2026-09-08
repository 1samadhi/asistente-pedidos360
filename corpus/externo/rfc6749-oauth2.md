# RFC 6749 — The OAuth 2.0 Authorization Framework

> **Fuente externa.** IETF, octubre 2012.
> https://www.rfc-editor.org/rfc/rfc6749.txt
>
> Extracto de las secciones pertinentes al caso. El documento completo
> se consulta en la URL indicada.


## 1.3. Authorization Grant

An authorization grant is a credential representing the resource
   owner's authorization (to access its protected resources) used by the
   client to obtain an access token.  This specification defines four
   grant types -- authorization code, implicit, resource owner password
   credentials, and client credentials -- as well as an extensibility
   mechanism for defining additional types.

## 1.4. Access Token

Access tokens are credentials used to access protected resources.  An
   access token is a string representing an authorization issued to the
   client.  The string is usually opaque to the client.  Tokens
   represent specific scopes and durations of access, granted by the
   resource owner, and enforced by the resource server and authorization
   server.

   The token may denote an identifier used to retrieve the authorization
   information or may self-contain the authorization information in a
   verifiable manner (i.e., a token string consisting of some data and a
   signature).  Additional authentication credentials, which are beyond
   the scope of this specification, may be required in order for the
   client to use a token.

   The access token provides an abstraction layer, replacing different
   authorization constructs (e.g., username and password) with a single
   token understood by the resource server.  This abstraction enables
   issuing access tokens more restrictive than the authorization grant
   used to obtain them, as well as removing the resource server's need
   to understand a wide range of authentication methods.

   Access tokens can have different formats, structures, and methods of
   utilization (e.g., cryptographic properties) based on the resource
   server security requirements.  Access token attributes and the
   methods used to access protected resources are beyond the scope of
   this specification and are defined by companion specifications such
   as [RFC6750].

## 1.5. Refresh Token

Refresh tokens are credentials used to obtain access tokens.  Refresh
   tokens are issued to the client by the authorization server and are
   used to obtain a new access token when the current access token
   becomes invalid or expires, or to obtain additional access tokens
   with identical or narrower scope (access tokens may have a shorter
   lifetime and fewer permissions than authorized by the resource
   owner).  Issuing a refresh token is optional at the discretion of the
   authorization server.  If the authorization server issues a refresh
   token, it is included when issuing an access token (i.e., step (D) in
   Figure 1).

   A refresh token is a string representing the authorization granted to
   the client by the resource owner.  The string is usually opaque to
   the client.  The token denotes an identifier used to retrieve the









   authorization information.  Unlike access tokens, refresh tokens are
   intended for use only with authorization servers and are never sent
   to resource servers.

  +--------+                                           +---------------+
  |        |--(A)------- Authorization Grant --------->|               |
  |        |                                           |               |
  |        |<-(B)----------- Access Token -------------|               |
  |        |               & Refresh Token             |               |
  |        |                                           |               |
  |        |                            +----------+   |               |
  |        |--(C)---- Access Token ---->|          |   |               |
  |        |                            |          |   |               |
  |        |<-(D)- Protected Resource --| Resource |   | Authorization |
  | Client |                            |  Server  |   |     Server    |
  |        |--(E)---- Access Token ---->|          |   |               |
  |        |                            |          |   |               |
  |        |<-(F)- Invalid Token Error -|          |   |               |
  |        |                            +----------+   |               |
  |        |                                           |               |
  |        |--(G)----------- Refresh Token ----------->|               |
  |        |                                           |               |
  |        |<-(H)----------- Access Token -------------|               |
  +--------+           & Optional Refresh Token        +---------------+

               Figure 2: Refreshing an Expired Access Token

   The flow illustrated in Figure 2 includes the following steps:

   (A)  The client requests an access token by authenticating with the
        authorization server and presenting an authorization grant.

   (B)  The authorization server authenticates the client and validates
        the authorization grant, and if valid, issues an access token
        and a refresh token.

   (C)  The client makes a protected resource request to the resource
        server by presenting the access token.

   (D)  The resource server validates the access token, and if valid,
        serves the request.

   (E)  Steps (C) and (D) repeat until the access token expires.  If the
        client knows the access token expired, it skips to step (G);
        otherwise, it makes another protected resource request.

   (F)  Since the access token is invalid, the resource server returns
        an invalid token error.







   (G)  The client requests a new access token by authenticating with
        the authorization server and presenting the refresh token.  The
        client authentication requirements are based on the client type
        and on the authorization server policies.

   (H)  The authorization server authenticates the client and validates
        the refresh token, and if valid, issues a new access token (and,
        optionally, a new refresh token).

   Steps (C), (D), (E), and (F) are outside the scope of this
   specification, as described in Section 7.

## 3.3. Access Token Scope

The authorization and token endpoints allow the client to specify the
   scope of the access request using the "scope" request parameter.  In
   turn, the authorization server uses the "scope" response parameter to
   inform the client of the scope of the access token issued.

   The value of the scope parameter is expressed as a list of space-
   delimited, case-sensitive strings.  The strings are defined by the
   authorization server.  If the value contains multiple space-delimited
   strings, their order does not matter, and each string adds an
   additional access range to the requested scope.

     scope       = scope-token *( SP scope-token )
     scope-token = 1*( %x21 / %x23-5B / %x5D-7E )

   The authorization server MAY fully or partially ignore the scope
   requested by the client, based on the authorization server policy or
   the resource owner's instructions.  If the issued access token scope
   is different from the one requested by the client, the authorization
   server MUST include the "scope" response parameter to inform the
   client of the actual scope granted.

   If the client omits the scope parameter when requesting
   authorization, the authorization server MUST either process the
   request using a pre-defined default value or fail the request
   indicating an invalid scope.  The authorization server SHOULD
   document its scope requirements and default value (if defined).

## 4.3. Resource Owner Password Credentials Grant

The resource owner password credentials grant type is suitable in
   cases where the resource owner has a trust relationship with the
   client, such as the device operating system or a highly privileged







   application.  The authorization server should take special care when
   enabling this grant type and only allow it when other flows are not
   viable.

   This grant type is suitable for clients capable of obtaining the
   resource owner's credentials (username and password, typically using
   an interactive form).  It is also used to migrate existing clients
   using direct authentication schemes such as HTTP Basic or Digest
   authentication to OAuth by converting the stored credentials to an
   access token.

     +----------+
     | Resource |
     |  Owner   |
     |          |
     +----------+
          v
          |    Resource Owner
         (A) Password Credentials
          |
          v
     +---------+                                  +---------------+
     |         |>--(B)---- Resource Owner ------->|               |
     |         |         Password Credentials     | Authorization |
     | Client  |                                  |     Server    |
     |         |<--(C)---- Access Token ---------<|               |
     |         |    (w/ Optional Refresh Token)   |               |
     +---------+                                  +---------------+

            Figure 5: Resource Owner Password Credentials Flow

   The flow illustrated in Figure 5 includes the following steps:

   (A)  The resource owner provides the client with its username and
        password.

   (B)  The client requests an access token from the authorization
        server's token endpoint by including the credentials received
        from the resource owner.  When making the request, the client
        authenticates with the authorization server.

   (C)  The authorization server authenticates the client and validates
        the resource owner credentials, and if valid, issues an access
        token.

## 4.4. Client Credentials Grant

The client can request an access token using only its client
   credentials (or other supported means of authentication) when the
   client is requesting access to the protected resources under its
   control, or those of another resource owner that have been previously
   arranged with the authorization server (the method of which is beyond
   the scope of this specification).








   The client credentials grant type MUST only be used by confidential
   clients.

     +---------+                                  +---------------+
     |         |                                  |               |
     |         |>--(A)- Client Authentication --->| Authorization |
     | Client  |                                  |     Server    |
     |         |<--(B)---- Access Token ---------<|               |
     |         |                                  |               |
     +---------+                                  +---------------+

                     Figure 6: Client Credentials Flow

   The flow illustrated in Figure 6 includes the following steps:

   (A)  The client authenticates with the authorization server and
        requests an access token from the token endpoint.

   (B)  The authorization server authenticates the client, and if valid,
        issues an access token.

## 5.1. Successful Response

The authorization server issues an access token and optional refresh
   token, and constructs the response by adding the following parameters
   to the entity-body of the HTTP response with a 200 (OK) status code:

   access_token
         REQUIRED.  The access token issued by the authorization server.

   token_type
         REQUIRED.  The type of the token issued as described in
         Section 7.1.  Value is case insensitive.

   expires_in
         RECOMMENDED.  The lifetime in seconds of the access token.  For
         example, the value "3600" denotes that the access token will
         expire in one hour from the time the response was generated.
         If omitted, the authorization server SHOULD provide the
         expiration time via other means or document the default value.









   refresh_token
         OPTIONAL.  The refresh token, which can be used to obtain new
         access tokens using the same authorization grant as described
         in Section 6.

   scope
         OPTIONAL, if identical to the scope requested by the client;
         otherwise, REQUIRED.  The scope of the access token as
         described by Section 3.3.

   The parameters are included in the entity-body of the HTTP response
   using the "application/json" media type as defined by [RFC4627].  The
   parameters are serialized into a JavaScript Object Notation (JSON)
   structure by adding each parameter at the highest structure level.
   Parameter names and string values are included as JSON strings.
   Numerical values are included as JSON numbers.  The order of
   parameters does not matter and can vary.

   The authorization server MUST include the HTTP "Cache-Control"
   response header field [RFC2616] with a value of "no-store" in any
   response containing tokens, credentials, or other sensitive
   information, as well as the "Pragma" response header field [RFC2616]
   with a value of "no-cache".

   For example:

     HTTP/1.1 200 OK
     Content-Type: application/json;charset=UTF-8
     Cache-Control: no-store
     Pragma: no-cache

     {
       "access_token":"2YotnFZFEjr1zCsicMWpAA",
       "token_type":"example",
       "expires_in":3600,
       "refresh_token":"tGzv3JOkF0XG5Qx2TlKWIA",
       "example_parameter":"example_value"
     }

   The client MUST ignore unrecognized value names in the response.  The
   sizes of tokens and other values received from the authorization
   server are left undefined.  The client should avoid making
   assumptions about value sizes.  The authorization server SHOULD
   document the size of any value it issues.

## 5.2. Error Response

The authorization server responds with an HTTP 400 (Bad Request)
   status code (unless specified otherwise) and includes the following
   parameters with the response:

   error
         REQUIRED.  A single ASCII [USASCII] error code from the
         following:

         invalid_request
               The request is missing a required parameter, includes an
               unsupported parameter value (other than grant type),
               repeats a parameter, includes multiple credentials,
               utilizes more than one mechanism for authenticating the
               client, or is otherwise malformed.

         invalid_client
               Client authentication failed (e.g., unknown client, no
               client authentication included, or unsupported
               authentication method).  The authorization server MAY
               return an HTTP 401 (Unauthorized) status code to indicate
               which HTTP authentication schemes are supported.  If the
               client attempted to authenticate via the "Authorization"
               request header field, the authorization server MUST
               respond with an HTTP 401 (Unauthorized) status code and
               include the "WWW-Authenticate" response header field
               matching the authentication scheme used by the client.

         invalid_grant
               The provided authorization grant (e.g., authorization
               code, resource owner credentials) or refresh token is
               invalid, expired, revoked, does not match the redirection
               URI used in the authorization request, or was issued to
               another client.

         unauthorized_client
               The authenticated client is not authorized to use this
               authorization grant type.

         unsupported_grant_type
               The authorization grant type is not supported by the
               authorization server.












         invalid_scope
               The requested scope is invalid, unknown, malformed, or
               exceeds the scope granted by the resource owner.

         Values for the "error" parameter MUST NOT include characters
         outside the set %x20-21 / %x23-5B / %x5D-7E.

   error_description
         OPTIONAL.  Human-readable ASCII [USASCII] text providing
         additional information, used to assist the client developer in
         understanding the error that occurred.
         Values for the "error_description" parameter MUST NOT include
         characters outside the set %x20-21 / %x23-5B / %x5D-7E.

   error_uri
         OPTIONAL.  A URI identifying a human-readable web page with
         information about the error, used to provide the client
         developer with additional information about the error.
         Values for the "error_uri" parameter MUST conform to the
         URI-reference syntax and thus MUST NOT include characters
         outside the set %x21 / %x23-5B / %x5D-7E.

   The parameters are included in the entity-body of the HTTP response
   using the "application/json" media type as defined by [RFC4627].  The
   parameters are serialized into a JSON structure by adding each
   parameter at the highest structure level.  Parameter names and string
   values are included as JSON strings.  Numerical values are included
   as JSON numbers.  The order of parameters does not matter and can
   vary.

   For example:

     HTTP/1.1 400 Bad Request
     Content-Type: application/json;charset=UTF-8
     Cache-Control: no-store
     Pragma: no-cache

     {
       "error":"invalid_request"
     }

## 7.1. Access Token Types

The access token type provides the client with the information
   required to successfully utilize the access token to make a protected
   resource request (along with type-specific attributes).  The client
   MUST NOT use an access token if it does not understand the token
   type.

   For example, the "bearer" token type defined in [RFC6750] is utilized
   by simply including the access token string in the request:

     GET /resource/1 HTTP/1.1
     Host: example.com
     Authorization: Bearer mF_9.B5f-4.1JqM

   while the "mac" token type defined in [OAuth-HTTP-MAC] is utilized by
   issuing a Message Authentication Code (MAC) key together with the
   access token that is used to sign certain components of the HTTP
   requests:

     GET /resource/1 HTTP/1.1
     Host: example.com
     Authorization: MAC id="h480djs93hd8",
                        nonce="274312:dj83hs9s",
                        mac="kDZvddkndxvhGRXZhvuDjEWhGeE="

   The above examples are provided for illustration purposes only.
   Developers are advised to consult the [RFC6750] and [OAuth-HTTP-MAC]
   specifications before use.

   Each access token type definition specifies the additional attributes
   (if any) sent to the client together with the "access_token" response
   parameter.  It also defines the HTTP authentication method used to
   include the access token when making a protected resource request.

## 10.3. Access Tokens

Access token credentials (as well as any confidential access token
   attributes) MUST be kept confidential in transit and storage, and
   only shared among the authorization server, the resource servers the
   access token is valid for, and the client to whom the access token is
   issued.  Access token credentials MUST only be transmitted using TLS
   as described in Section 1.6 with server authentication as defined by
   [RFC2818].

   When using the implicit grant type, the access token is transmitted
   in the URI fragment, which can expose it to unauthorized parties.

   The authorization server MUST ensure that access tokens cannot be
   generated, modified, or guessed to produce valid access tokens by
   unauthorized parties.

   The client SHOULD request access tokens with the minimal scope
   necessary.  The authorization server SHOULD take the client identity
   into account when choosing how to honor the requested scope and MAY
   issue an access token with less rights than requested.

   This specification does not provide any methods for the resource
   server to ensure that an access token presented to it by a given
   client was issued to that client by the authorization server.
