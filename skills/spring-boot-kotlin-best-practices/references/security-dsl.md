# Spring Security 6.x Kotlin DSL — Full Examples

> SKILL.md 섹션 11(Security)의 보조 자료. Kotlin DSL 기반 SecurityFilterChain, JWT Resource Server, OAuth2 Client, method security, CSRF/CORS 결정, 패스워드 인코더 세부 설정.

## 1. 기본 SecurityFilterChain (REST + JWT)

```kotlin
@Configuration
@EnableWebSecurity
class SecurityConfig(private val jwtDecoder: JwtDecoder) {

    @Bean
    fun securityFilterChain(http: HttpSecurity): SecurityFilterChain = http {
        csrf { disable() }
        cors { configurationSource = corsConfigurationSource() }
        sessionManagement { sessionCreationPolicy = SessionCreationPolicy.STATELESS }
        authorizeHttpRequests {
            authorize("/actuator/health", permitAll)
            authorize("/actuator/**", hasRole("OPS"))
            authorize("/api/v1/public/**", permitAll)
            authorize("/api/v1/admin/**", hasRole("ADMIN"))
            authorize("/api/v1/users/me", authenticated)
            authorize(HttpMethod.POST, "/api/v1/users", permitAll) // 회원가입
            authorize(anyRequest, authenticated)
        }
        oauth2ResourceServer {
            jwt {
                jwtDecoder = this@SecurityConfig.jwtDecoder
                jwtAuthenticationConverter = jwtAuthenticationConverter()
            }
        }
        exceptionHandling {
            authenticationEntryPoint = BearerTokenAuthenticationEntryPoint()
            accessDeniedHandler = BearerTokenAccessDeniedHandler()
        }
        headers {
            frameOptions { sameOrigin = true }
            contentSecurityPolicy { policyDirectives = "default-src 'self'" }
            referrerPolicy { policy = ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN }
        }
    }.build()

    private fun corsConfigurationSource(): CorsConfigurationSource {
        val config = CorsConfiguration().apply {
            allowedOrigins = listOf("https://app.example.com")
            allowedMethods = listOf("GET", "POST", "PUT", "DELETE", "PATCH")
            allowedHeaders = listOf("Authorization", "Content-Type", "Idempotency-Key")
            exposedHeaders = listOf("X-Trace-Id")
            allowCredentials = true
            maxAge = 3600
        }
        return UrlBasedCorsConfigurationSource().apply { registerCorsConfiguration("/**", config) }
    }

    private fun jwtAuthenticationConverter(): JwtAuthenticationConverter =
        JwtAuthenticationConverter().apply {
            setJwtGrantedAuthoritiesConverter { jwt ->
                val roles = jwt.getClaimAsStringList("roles") ?: emptyList()
                roles.map { SimpleGrantedAuthority("ROLE_$it") }
            }
        }

    @Bean
    fun jwtDecoder(@Value("\${app.security.jwt.issuer-uri}") issuerUri: String): JwtDecoder =
        NimbusJwtDecoder.withJwkSetUri("$issuerUri/.well-known/jwks.json").build()
}
```

## 2. 패스워드 인코딩 (BCrypt + 마이그레이션)

```kotlin
@Configuration
class PasswordConfig {
    @Bean
    fun passwordEncoder(): PasswordEncoder {
        val encoders = mapOf<String, PasswordEncoder>(
            "bcrypt" to BCryptPasswordEncoder(12),
            "argon2" to Argon2PasswordEncoder.defaultsForSpringSecurity_v5_8(),
            "noop" to NoOpPasswordEncoder.getInstance(), // 절대 production에 쓰지 마라
        )
        return DelegatingPasswordEncoder("bcrypt", encoders)
    }
}
```

`DelegatingPasswordEncoder`는 저장된 해시의 prefix(`{bcrypt}...`, `{argon2}...`)로 알고리즘을 식별해 검증한다. 새 가입은 `bcrypt`, 기존 SHA-1 등은 검증만 가능한 형태로 마이그레이션할 수 있다.

### BCrypt strength 결정
- 12 (기본 권장) — 운영 CPU에서 약 200~400ms 처리. 대부분의 웹앱에 적합.
- 10 — 빠른 로그인이 필요한 환경, 보안 트레이드오프 인지하고 결정.
- 13~14 — 매우 민감한 시스템. 로그인 시 사용자 체감 지연 고려.

### Argon2 (권장 신규)
```kotlin
@Bean
fun passwordEncoder(): PasswordEncoder = Argon2PasswordEncoder(
    16,    // saltLength
    32,    // hashLength
    1,     // parallelism
    65536, // memory (KB) = 64 MiB
    4,     // iterations
)
```

OWASP 권장값. 메모리 비용이 높아 GPU 공격에 저항.

## 3. JWT 발급 (Resource Server가 아니라 직접 발급할 때)

```kotlin
@Configuration
class JwtIssuerConfig {

    @Bean
    fun jwtEncoder(@Value("\${app.security.jwt.private-key}") privateKeyResource: Resource): JwtEncoder {
        val rsaKey = readRsaKey(privateKeyResource)
        val jwkSource = ImmutableJWKSet<SecurityContext>(JWKSet(rsaKey))
        return NimbusJwtEncoder(jwkSource)
    }

    private fun readRsaKey(resource: Resource): RSAKey = TODO("PEM 파싱")
}

@Service
class TokenService(private val encoder: JwtEncoder, private val clock: Clock) {
    fun issue(user: User): String {
        val now = clock.instant()
        val claims = JwtClaimsSet.builder()
            .issuer("https://auth.example.com")
            .subject(user.id.value.toString())
            .audience(listOf("order-service"))
            .issuedAt(now)
            .expiresAt(now.plus(Duration.ofMinutes(15)))
            .claim("roles", user.roles.map { it.name })
            .build()
        return encoder.encode(JwtEncoderParameters.from(claims)).tokenValue
    }
}
```

## 4. Method Security (`@PreAuthorize`, `@PostAuthorize`)

```kotlin
@Configuration
@EnableMethodSecurity(prePostEnabled = true)
class MethodSecurityConfig

@Service
class OrderService(private val repository: OrderRepository) {

    @PreAuthorize("hasRole('ADMIN') or #ownerId == authentication.name")
    suspend fun findByOwner(ownerId: String): List<Order> = repository.findByOwner(ownerId)

    @PostAuthorize("returnObject == null or returnObject.ownerId == authentication.name or hasRole('ADMIN')")
    suspend fun findById(id: OrderId): Order? = repository.findById(id)

    @PreAuthorize("@orderPolicy.canCancel(#id, authentication)")
    suspend fun cancel(id: OrderId) { /* ... */ }
}

@Component("orderPolicy")
class OrderPolicy(private val repository: OrderRepository) {
    suspend fun canCancel(id: OrderId, auth: Authentication): Boolean {
        val order = repository.findById(id) ?: return false
        return order.ownerId == auth.name || auth.authorities.any { it.authority == "ROLE_ADMIN" }
    }
}
```

SpEL 표현식은 강력하지만 디버깅이 어렵다. 복잡한 정책은 `@Component`로 분리해 단위 테스트 가능하게 만든다.

## 5. CSRF 정책 결정

| 시나리오 | CSRF |
|---------|------|
| REST API + JWT in Authorization header | disable (브라우저가 자동 부착 안 함) |
| REST API + 쿠키 기반 세션 | **활성** (CSRF 토큰 + SameSite=Strict 쿠키) |
| Server-rendered HTML (Thymeleaf) | 활성 |
| 공개 API (외부 시스템이 호출) | API key + IP allowlist + 활성 disable |

### 세션 + CSRF 토큰
```kotlin
fun securityFilterChain(http: HttpSecurity): SecurityFilterChain = http {
    csrf {
        csrfTokenRepository = CookieCsrfTokenRepository.withHttpOnlyFalse()
        csrfTokenRequestHandler = CsrfTokenRequestAttributeHandler().apply {
            setCsrfRequestAttributeName(null) // BREACH 공격 방어
        }
    }
    // ...
}.build()
```

## 6. OAuth2 Client (외부 IdP 로그인)

```kotlin
@Configuration
class OAuth2ClientConfig {
    @Bean
    fun securityFilterChain(http: HttpSecurity): SecurityFilterChain = http {
        oauth2Login {
            loginPage = "/login"
            defaultSuccessUrl("/dashboard", true)
            userInfoEndpoint { userService = customOAuth2UserService() }
        }
        // ...
    }.build()

    @Bean
    fun customOAuth2UserService(): OAuth2UserService<OAuth2UserRequest, OAuth2User> =
        DefaultOAuth2UserService() // 또는 커스텀 변환
}
```

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          google:
            client-id: ${GOOGLE_CLIENT_ID}
            client-secret: ${GOOGLE_CLIENT_SECRET}
            scope: openid, profile, email
        provider:
          google:
            issuer-uri: https://accounts.google.com
```

## 7. 비밀 회전과 키 관리

JWT 서명 키, OAuth client secret, DB 비밀번호는 코드에 절대 들어가지 않는다.

- **로컬 개발**: `application-local.yml` + `.gitignore` (또는 `local.properties`)
- **CI**: GitHub Secrets / Vault / AWS Secrets Manager 주입
- **운영**: Spring Cloud Config + Vault, AWS Secrets Manager + IAM, Kubernetes Secrets (KMS encrypted)

### JWT 서명 키 회전
```yaml
app:
  security:
    jwt:
      issuer-uri: https://auth.example.com
      # JWK Set URI에서 kid로 식별. 회전 시 두 키를 동시에 제공하다가 점진적 교체.
```

`jwtDecoder`가 JWK Set URI를 캐싱하므로 회전 시 캐시 무효화 정책을 확인한다.

## 8. CORS 결정 표

| 시나리오 | allowedOrigins | allowCredentials | 비고 |
|---------|----------------|-------------------|------|
| SPA + JWT(Authorization 헤더) | 명시 도메인 | false | JWT는 헤더라 credentials 불필요 |
| SPA + 쿠키 세션 | 명시 도메인 | true | `*` 안 됨. 정확한 origin 필요 |
| 모바일 앱(WKWebView) | 필요 시 명시 도메인 | 상황별 | 보통 별도 API gateway |
| 공개 API | `*` 또는 broad | false | 인증은 API key |

`allowedOrigins = ["*"]` + `allowCredentials = true`는 브라우저가 거부한다 (CORS 사양). 항상 둘 중 하나는 좁혀야 한다.

## 9. 흔한 보안 회귀 패턴

| 패턴 | 결과 | 대응 |
|------|------|------|
| 라우트 추가 시 `authorize("/api/**", permitAll)` 임시 | production 진입 | 화이트리스트가 아니라 블랙리스트 패턴 = 위험. authenticated 기본 + 명시 permit |
| `hasRole("admin")` (소문자) | role mismatch (`ROLE_ADMIN` 비교) | enum/상수 사용, 또는 `hasAuthority("ROLE_ADMIN")` 명시 |
| `@PreAuthorize` 누락한 admin 엔드포인트 | 인가 우회 | URL 패턴 매칭과 method security를 함께 사용 |
| JWT 만료 시간 24시간+ | 탈취 시 위험 노출 시간 ↑ | access 15분 + refresh token 분리 |
| 비밀번호 reset 토큰을 GET query string | URL 로그·history에 남음 | POST body, single-use, TTL 10분 |
| CSRF disable 후 잊기 | 쿠키 기반 인증 도입 시 취약 | 환경별 정책 명시화, 코드 주석 |

## 10. 테스트 지원

```kotlin
@WebMvcTest(OrderController::class)
@Import(SecurityConfig::class)
class OrderControllerSecurityTest {

    @Test
    @WithAnonymousUser
    fun `익명 사용자 — 401`() { /* ... */ }

    @Test
    @WithMockUser(username = "alice", roles = ["USER"])
    fun `USER 권한 — 자기 주문은 조회 가능`() { /* ... */ }

    @Test
    fun `JWT 환경에서는 mockJwt 사용`() {
        mockMvc.get("/api/v1/orders") {
            with(SecurityMockMvcRequestPostProcessors.jwt()
                .authorities(SimpleGrantedAuthority("ROLE_ADMIN")))
        }.andExpect { status { isOk() } }
    }
}
```

`@WithMockUser`는 단순 사용자 컨텍스트, JWT 기반이면 `jwt()` postProcessor를 사용해 실제 인증 흐름에 가깝게 검증한다.
