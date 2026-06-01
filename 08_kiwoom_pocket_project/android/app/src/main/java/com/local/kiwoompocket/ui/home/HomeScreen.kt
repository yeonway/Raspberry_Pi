package com.local.kiwoompocket.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.local.kiwoompocket.core.util.NumberFormatters
import com.local.kiwoompocket.ui.components.ErrorView
import com.local.kiwoompocket.ui.components.InfoCard
import com.local.kiwoompocket.ui.components.LoadingView

@Composable
fun HomeScreen(state: HomeUiState, onRefresh: () -> Unit, onSettings: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        NoticeCard()
        InfoCard(title = "서버 연결 상태") {
            Text(state.serverMessage)
            Text("서버 주소: ${state.settings.serverBaseUrl.ifBlank { "미설정" }}")
            TextButtonLike(text = "연결 테스트", onClick = onRefresh)
        }
        InfoCard(title = "키움 토큰 상태") {
            val token = state.tokenStatus
            Text(if (token?.hasToken == true) "토큰 보유: ${token.maskedToken.orEmpty()}" else "토큰 없음")
            Text("키움 키 설정: ${if (token?.hasCredentials == true) "완료" else "미설정"}")
        }
        InfoCard(title = "계좌 요약") {
            val balance = state.balance
            if (balance == null) {
                Text("계좌 데이터를 불러오지 못했습니다.")
            } else {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("예수금")
                    Text(NumberFormatters.won(balance.deposit), fontWeight = FontWeight.SemiBold)
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("총자산")
                    Text(NumberFormatters.won(balance.totalAsset), fontWeight = FontWeight.SemiBold)
                }
            }
        }
        InfoCard(title = "관심종목") {
            if (state.watchlist.isEmpty()) {
                Text("관심종목이 비어 있습니다.")
            } else {
                state.watchlist.take(5).forEach { Text("${it.code}  ${it.name}") }
            }
        }
        if (state.loading) LoadingView()
        state.error?.let { ErrorView(message = it, onRetry = onRefresh) }
        TextButtonLike(text = "설정으로 이동", onClick = onSettings)
    }
}

@Composable
private fun NoticeCard() {
    InfoCard(title = "안내") {
        Text("이 앱은 투자 추천을 제공하지 않습니다.")
        Text("실전 주문은 기본 비활성화되어 있습니다.")
        Text("키움 API 키는 Android 앱에 저장하지 않습니다.")
    }
}

@Composable
private fun TextButtonLike(text: String, onClick: () -> Unit) {
    androidx.compose.material3.OutlinedButton(onClick = onClick) {
        Text(text)
    }
}
