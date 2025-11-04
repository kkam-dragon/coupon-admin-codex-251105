document.addEventListener('DOMContentLoaded', function() {
    // flatpickr 초기화
    flatpickr("#dispatchDateTime", {
        wrap: true,
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        time_24hr: true,
        locale: "ko"
    });

    // 기본값 설정
    const salesManagerInput = document.getElementById('salesManager');
    if (salesManagerInput) salesManagerInput.value = '심재준';
    
    const senderPhoneInput = document.getElementById('senderPhone');
    if (senderPhoneInput) senderPhoneInput.value = '16683551';


    // 글자수 제한 필드 설정
    const fieldsToTrack = [
        { id: 'clientName', maxLength: 30 },
        { id: 'salesManager', maxLength: 30 },
        { id: 'clientRequester', maxLength: 30 },
        { id: 'requesterPhone', maxLength: 11 },
        { id: 'requesterEmail', maxLength: 30 },
        { id: 'eventName', maxLength: 50 },
        { id: 'mmsTitle', maxLength: 20 },
        { id: 'mmsContent', maxLength: 200 },
        { id: 'senderPhone', maxLength: 11 }
    ];

    fieldsToTrack.forEach(field => {
        const inputElement = document.getElementById(field.id);
        const feedbackElement = document.getElementById(`${field.id}-feedback`);
        if (inputElement && feedbackElement) {
            // 초기 글자수 표시
            updateCharCount(inputElement, feedbackElement);
            // 입력 시 글자수 업데이트
            inputElement.addEventListener('input', () => updateCharCount(inputElement, feedbackElement));
        }
    });

    // 이메일 유효성 검사
    const emailInput = document.getElementById('requesterEmail');
    if (emailInput) {
        emailInput.addEventListener('input', validateEmail);
    }

    // 배너 이미지 사용 여부 체크박스 로직
    const useBannerCheckbox = document.getElementById('useBannerImage');
    const bannerImageInput = document.getElementById('bannerImage');

    if (useBannerCheckbox && bannerImageInput) {
        useBannerCheckbox.addEventListener('change', function() {
            // 체크박스가 선택되면 파일 입력을 활성화하고, 그렇지 않으면 비활성화합니다.
            bannerImageInput.disabled = !this.checked;
        });
    }

    // 간편등록 수신자 목록 입력 처리
    const recipientListTextarea = document.getElementById('recipientList');
    const recipientLineNumbersElement = document.getElementById('recipientLineNumbers');
    const recipientValidationElement = document.getElementById('recipientValidation');
    const recipientCountElement = document.getElementById('recipientCount');
    const resetSimpleRegBtn = document.getElementById('resetSimpleRegBtn');

    let isPasting = false; // 붙여넣기 동작을 감지하기 위한 플래그

    if (recipientListTextarea && recipientCountElement && recipientValidationElement && recipientLineNumbersElement && resetSimpleRegBtn) {
        // 붙여넣기 이벤트 감지
        recipientListTextarea.addEventListener('paste', () => {
            isPasting = true; // 붙여넣기가 시작되면 플래그를 true로 설정
            // 사용자에게 붙여넣기가 완료되었음을 시각적으로 알림
            recipientListTextarea.style.transition = 'background-color 0.3s ease';
            recipientListTextarea.style.backgroundColor = '#e8f0fe'; // 연한 파란색으로 변경

            // 잠시 후 원래 배경색으로 복원
            setTimeout(() => {
                recipientListTextarea.style.backgroundColor = '';
            }, 500);
        });

        const handleRecipientInput = (e) => {
            const MAX_RECIPIENTS = 100;
            const { value, selectionStart } = e.target;
            const lines = value.split('\n');

            // 1. 각 줄을 순회하며 숫자만 남기고 11자로 제한 (100건 제한 전)
            let processedLines = lines.map(line => {
                const numericLine = line.replace(/[^0-9]/g, ''); // 숫자 이외의 문자 제거
                return numericLine.substring(0, 11); // 11자로 제한
            });

            // 1-1. 100건 초과 입력 처리
            if (processedLines.length > MAX_RECIPIENTS) {
                if (isPasting) {
                    alert('100개가 초과되었습니다. 초과된 휴대폰은 삭제됩니다.');
                }
                // 100건으로 자르기
                processedLines = processedLines.slice(0, MAX_RECIPIENTS);
            }
            // 붙여넣기 처리가 끝났으므로 플래그를 리셋
            isPasting = false;

            // 2. 연속된 빈 줄을 하나로 합침 (사용자 경험을 위해 마지막 줄이 비어있는 경우는 허용)
            let compactedValue = processedLines.join('\n').replace(/\n{2,}/g, '\n');

            // 3. 최종적으로 처리된 값을 textarea에 반영
            const newValue = compactedValue;

            // 변경된 내용으로 값을 업데이트
            e.target.value = newValue;

            // 커서 위치 보정: 불필요한 문자가 제거된 만큼만 커서를 이동시켜 사용자 경험을 해치지 않도록 함
            const diff = value.length - newValue.length;
            e.target.selectionStart = selectionStart - diff;
            e.target.selectionEnd = selectionStart - diff;

            // 비어있지 않은 줄의 개수를 세어 카운트 업데이트
            const lineCount = newValue.split('\n').filter(line => line.trim() !== '').length;

            // 유효성 검사 및 O, X 표시
            const validationResults = newValue.split('\n').map(line => {
                const trimmedLine = line.trim();
                if (trimmedLine === '') return ''; // 빈 줄은 아무것도 표시 안 함

                // 1. 첫 두 자리가 '01'로 시작하지 않으면 무조건 X
                if (!trimmedLine.startsWith('01')) {
                    return '<span class="text-danger">X</span>';
                }

                // 2. '01'로 시작하는 경우, 세부 길이 규칙 적용
                // '010'으로 시작하면 11자리여야 유효
                if (trimmedLine.startsWith('010')) {
                    return trimmedLine.length === 11 ? '<span class="text-success">O</span>' : '<span class="text-danger">X</span>';
                }
                // 그 외 '01x'의 경우 10자리 또는 11자리여야 유효
                return (trimmedLine.length === 10 || trimmedLine.length === 11) ? '<span class="text-success">O</span>' : '<span class="text-danger">X</span>';
            }).join('<br>');

            // 줄 번호 생성 및 표시
            const lineNumbers = newValue.split('\n').map((_, index) => index + 1).join('<br>');

            recipientLineNumbersElement.innerHTML = lineNumbers;
            recipientValidationElement.innerHTML = validationResults;
            recipientCountElement.textContent = `${lineCount} / ${MAX_RECIPIENTS}건`;
        };

        // input 이벤트는 타이핑과 붙여넣기 모두에서 발생
        recipientListTextarea.addEventListener('input', handleRecipientInput);
        handleRecipientInput({ target: recipientListTextarea }); // 초기 로딩 시 한 번 실행하여 1번 줄을 표시

        // 'Enter' 키 입력 시 유효성 검사
        recipientListTextarea.addEventListener('keydown', (e) => {
            // 엔터키가 아니면 함수 종료
            if (e.key !== 'Enter') return;

            // 현재 줄 수를 확인하여 100건을 초과하는 입력을 막음 (타이핑 시)
            const currentLineCount = e.target.value.split('\n').length;
            if (currentLineCount >= 100) {
                e.preventDefault();
                alert('100개까지만 입력이 가능합니다.');
                return; // 더 이상 진행하지 않음
            }

            const { value, selectionStart } = e.target;

            // 커서 위치 바로 앞까지의 텍스트를 기반으로 현재 줄 찾기
            const textBeforeCursor = value.substring(0, selectionStart);
            const currentLine = textBeforeCursor.split('\n').pop() || '';

            // 조건 1: 010으로 시작하지만 11자리가 아닐 경우
            const isInvalid010 = currentLine.startsWith('010') && currentLine.length !== 11;
            // 조건 2: 현재 줄이 비어있는 경우 (불필요한 빈 줄 생성 방지)
            const isCreatingEmptyLine = currentLine.trim() === '';

            if (isInvalid010 || isCreatingEmptyLine) {
                e.preventDefault(); // 엔터 키의 기본 동작(줄바꿈)을 막음

                // 사용자에게 시각적 피드백 제공 (입력창 흔들기)
                recipientListTextarea.classList.add('is-invalid-shake');
                setTimeout(() => {
                    recipientListTextarea.classList.remove('is-invalid-shake');
                }, 500);
            }
        });

        recipientListTextarea.addEventListener('scroll', () => {
            recipientValidationElement.scrollTop = recipientListTextarea.scrollTop;
            recipientLineNumbersElement.scrollTop = recipientListTextarea.scrollTop;
        });

        // 간편등록 초기화 버튼 클릭 이벤트
        resetSimpleRegBtn.addEventListener('click', () => {
            // 입력 내용이 있을 때만 모달 팝업을 띄움
            if (recipientListTextarea.value.trim() !== '') {
                showUnsavedChangesModal(
                    () => resetSimpleRegistration(true), // 확인 시 강제 초기화
                    "입력한 모든 휴대폰 번호를 초기화하시겠습니까?"
                );
            }
        });
    }

    // 대량등록(엑셀) 탭 로직
    const excelFileInput = document.getElementById('excelFileInput');
    const excelPreviewContainer = document.getElementById('excelPreviewContainer');
    const excelPreviewBody = document.getElementById('excelPreviewBody');
    const excelRecipientCount = document.getElementById('excelRecipientCount');
    const resetExcelFileBtn = document.getElementById('resetExcelFileBtn');

    if (excelFileInput && excelPreviewContainer && excelPreviewBody && excelRecipientCount && resetExcelFileBtn) {
        excelFileInput.addEventListener('change', async (event) => {
            const file = event.target.files[0];
            const MAX_EXCEL_RECIPIENTS = 20000;

            // 파일 미선택 시 초기화
            if (!file) {
                resetExcelUpload();
                return;
            }
            
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const data = new Uint8Array(e.target.result);
                    const workbook = XLSX.read(data, { type: 'array' });
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    const json = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: "" });

                    if (json.length > MAX_EXCEL_RECIPIENTS) {
                        alert('대량 업로드 가능 휴대폰 번호 개수는 20,000건입니다. 확인 후 재업로드 하세요.');
                        throw new Error('Recipient count exceeded');
                    }

                    const validatedPhones = [];
                    for (const row of json) {
                        const originalPhone = String(row[0] || '').trim();
                        if (originalPhone === '') continue; // 빈 행은 건너뜀

                        // 규칙 2: 허용되지 않은 특수문자/공백 체크 (하이픈 제외)
                        if (/[^0-9-]/.test(originalPhone)) throw new Error('휴대폰 번호에 허용되지 않은 문자(공백, 특수문자)가 포함되어 있습니다.');

                        // 규칙 4: 하이픈 제거
                        const phone = originalPhone.replace(/-/g, '');

                        // 규칙 1: '01'로 시작하는지 체크
                        if (!phone.startsWith('01')) throw new Error("'01'로 시작하지 않는 휴대폰 번호가 있습니다.");

                        // 규칙 3: '010' 시작 시 11자리인지 체크
                        if (phone.startsWith('010') && phone.length !== 11) throw new Error("'010'으로 시작하는 번호가 11자리가 아닙니다.");

                        // (추가) 그 외 '01x' 번호는 10자리 또는 11자리인지 체크
                        if (!phone.startsWith('010') && (phone.length < 10 || phone.length > 11)) throw new Error("휴대폰 번호의 길이가 올바르지 않습니다.");

                        validatedPhones.push(phone);
                    }

                    // 모든 유효성 검사 통과 시 목록 표시
                    excelPreviewBody.innerHTML = validatedPhones.map((phone, index) => `
                        <tr>
                            <td>${index + 1}</td>
                            <td>${phone}</td>
                        </tr>
                    `).join('');
                    excelRecipientCount.textContent = `총 ${validatedPhones.length}건`;
                    excelPreviewContainer.style.display = 'block';

                } catch (error) {
                    // 유효성 검사 실패 또는 파일 처리 오류 시
                    alert(error.message + '\n\n확인 후 재업로드 하세요.');
                    resetExcelUpload();
                }
            };
            reader.readAsArrayBuffer(file);
        });

        // 초기화 버튼 클릭 이벤트
        resetExcelFileBtn.addEventListener('click', () => {
            // 파일이 선택되어 있을 때만 모달 팝업을 띄움
            if (excelFileInput.value) {
                showUnsavedChangesModal(
                    resetExcelUpload,
                    "선택한 파일 정보를 초기화하시겠습니까?"
                );
            }
        });
    }

    /**
     * 엑셀 업로드 관련 UI를 초기화하는 함수
     */
    function resetExcelUpload() {
        if (excelFileInput) excelFileInput.value = '';
        if (excelPreviewContainer) excelPreviewContainer.style.display = 'none';
        if (excelPreviewBody) excelPreviewBody.innerHTML = '';
        if (excelRecipientCount) excelRecipientCount.textContent = '총 0건';
    }

    /**
     * 간편등록 관련 UI를 초기화하는 함수
     */
    function resetSimpleRegistration() {
        if (recipientListTextarea) recipientListTextarea.value = '';
        // input 이벤트를 수동으로 발생시켜 채번, 유효성, 카운트를 모두 초기화
        if (recipientListTextarea) {
            recipientListTextarea.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }
});

// 탭 전환 시 데이터 초기화 로직
document.addEventListener('DOMContentLoaded', function() {
    const simpleRegTab = document.getElementById('simple-reg-tab');
    const bulkRegTab = document.getElementById('bulk-reg-tab');
    const recipientListTextarea = document.getElementById('recipientList');
    const excelFileInput = document.getElementById('excelFileInput');

    const tabs = [simpleRegTab, bulkRegTab];

    tabs.forEach(tab => {
        if (tab) {
            tab.addEventListener('show.bs.tab', function(event) {
                const previousTab = event.relatedTarget; // 떠나는 탭
                let dataExists = false;

                if (previousTab) {
                    if (previousTab.id === 'simple-reg-tab' && recipientListTextarea && recipientListTextarea.value.trim() !== '') {
                        dataExists = true;
                    } else if (previousTab.id === 'bulk-reg-tab' && excelFileInput && excelFileInput.value !== '') {
                        dataExists = true;
                    }
                }

                if (dataExists) {
                    if (!confirm('다른 탭으로 이동하면 현재 입력된 내용이 삭제됩니다. 이동하시겠습니까?')) {
                        event.preventDefault(); // 사용자가 '취소'를 누르면 탭 전환을 막음
                    }
                    // '확인'을 누르면 탭 전환이 계속 진행되고, 아래 'hide.bs.tab' 이벤트에서 초기화가 실행됨
                }
            });

            tab.addEventListener('hide.bs.tab', function(event) {
                // 이 이벤트는 'show.bs.tab'에서 preventDefault가 호출되지 않았을 때만 발생
                if (event.target.id === 'simple-reg-tab') {
                    resetSimpleRegistration(true); // 확인창 없이 강제 초기화
                } else if (event.target.id === 'bulk-reg-tab') {
                    resetExcelUpload();
                }
            });
        }
    });
});

// 탭 전환 시 데이터 초기화 로직
document.addEventListener('DOMContentLoaded', function() {
    const simpleRegTab = document.getElementById('simple-reg-tab');
    const bulkRegTab = document.getElementById('bulk-reg-tab');
    const recipientListTextarea = document.getElementById('recipientList');
    const excelFileInput = document.getElementById('excelFileInput');

    const tabs = [simpleRegTab, bulkRegTab];

    tabs.forEach(tab => {
        if (tab) {
            tab.addEventListener('show.bs.tab', function(event) {
                const previousTab = event.relatedTarget; // 떠나는 탭
                let dataExists = false;

                if (previousTab) {
                    if (previousTab.id === 'simple-reg-tab' && recipientListTextarea && recipientListTextarea.value.trim() !== '') {
                        dataExists = true;
                    } else if (previousTab.id === 'bulk-reg-tab' && excelFileInput && excelFileInput.value !== '') {
                        dataExists = true;
                    }
                }

                if (dataExists) {
                    if (!confirm('다른 탭으로 이동하면 현재 입력된 내용이 삭제됩니다. 이동하시겠습니까?')) {
                        event.preventDefault(); // 사용자가 '취소'를 누르면 탭 전환을 막음
                    }
                    // '확인'을 누르면 탭 전환이 계속 진행되고, 아래 'hide.bs.tab' 이벤트에서 초기화가 실행됨
                }
            });

            tab.addEventListener('hide.bs.tab', function(event) {
                // 이 이벤트는 'show.bs.tab'에서 preventDefault가 호출되지 않았을 때만 발생
                if (event.target.id === 'simple-reg-tab') {
                    resetSimpleRegistration(true); // 확인창 없이 강제 초기화
                } else if (event.target.id === 'bulk-reg-tab') {
                    resetExcelUpload();
                }
            });
        }
    });

    // 저장/발송 및 취소 버튼 로직
    const sendBtn = document.getElementById('sendBtn');
    const cancelBtn = document.getElementById('cancelBtn');

    // '취소' 버튼 클릭 이벤트
    if (cancelBtn) { // cancelBtn이 존재하는 페이지(sendCoupon.html)에서만 실행
        cancelBtn.addEventListener('click', (e) => {
            e.preventDefault(); // a 태그처럼 기본 동작을 막음
            const cancelMessage = "작성 중인 내용이 모두 사라집니다.<br>정말 취소하시겠습니까?";
            if (isSendCouponFormDirty()) {
                showUnsavedChangesModal(
                    () => {
                        allowNavigation = true;
                        location.reload();
                    }, cancelMessage
                );
            } else {
                location.reload();
            }
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', () => {
            // 필수 항목 유효성 검사
            const requiredFields = [
                { id: 'clientName', name: '고객사' },
                { id: 'salesManager', name: '영업담당자' },
                { id: 'clientRequester', name: '고객사 요청자' },
                { id: 'requesterEmail', name: '요청자 이메일' },
                { id: 'eventName', name: '이벤트명' },
                { id: 'dispatchDateTime', name: '발송 예약일시' },
                { id: 'productName', name: '상품명' },
                { id: 'mmsTitle', name: '제목' },
                { id: 'mmsContent', name: '내용' },
                { id: 'senderPhone', name: '발신자 번호' }
            ];

            for (const field of requiredFields) {
                const element = document.getElementById(field.id);
                // dispatchDateTime은 내부의 input을 확인
                const value = field.id === 'dispatchDateTime' ? element.querySelector('input').value : element.value;

                if (!value.trim()) {
                    alert(`필수 항목인 '${field.name}'을(를) 입력해주세요.`);
                    if (field.id === 'dispatchDateTime') {
                        element.querySelector('input').focus();
                    } else {
                        element.focus();
                    }
                    return;
                }
            }

            // 수신자 번호 유효성 검사
            const activeTab = document.querySelector('#recipient-tabs .nav-link.active');
            let recipientCount = 0;

            if (activeTab.id === 'simple-reg-tab') {
                const recipientList = document.getElementById('recipientList').value;
                const validationResults = document.getElementById('recipientValidation').innerHTML;
                if (recipientList.trim() === '') {
                    alert('간편등록에 수신자 휴대폰 번호를 입력해주세요.');
                    document.getElementById('recipientList').focus();
                    return;
                }
                if (validationResults.includes('text-danger')) {
                    alert('간편등록에 유효하지 않은 휴대폰 번호가 있습니다. (X 표시 확인)');
                    document.getElementById('recipientList').focus();
                    return;
                }
                recipientCount = recipientList.split('\n').filter(line => line.trim() !== '').length;
            } else if (activeTab.id === 'bulk-reg-tab') {
                const excelFile = document.getElementById('excelFileInput').value;
                if (excelFile === '') {
                    alert('대량등록(엑셀)에 파일을 업로드해주세요.');
                    document.getElementById('excelFileInput').focus();
                    return;
                }
                const countText = document.getElementById('excelRecipientCount').textContent;
                recipientCount = parseInt(countText.replace(/[^0-9]/g, ''), 10);
            }

            if (recipientCount === 0) {
                alert('등록된 수신자 휴대폰 번호가 없습니다.');
                return;
            }

            // 모든 유효성 검사 통과 시
            const dispatchDateTime = document.querySelector('#dispatchDateTime input').value;
            const productName = document.getElementById('productName').value;
            if (confirm(`${dispatchDateTime}에 ${productName}을(를) 총 ${recipientCount}개의 휴대폰 번호로 발송이 됩니다. 정말 발송하시겠습니까?`)) {
                alert('발송 요청이 완료되었습니다.');
                location.reload(); // 성공 후 페이지 새로고침
            }
        });
    }
});

/**
 * 입력 필드의 글자 수를 세어 피드백 요소에 표시하는 함수
 * @param {HTMLInputElement|HTMLTextAreaElement} inputElement - 글자 수를 셀 입력 요소
 * @param {HTMLElement} feedbackElement - 글자 수를 표시할 요소
 */
function updateCharCount(inputElement, feedbackElement) {
    const currentLength = inputElement.value.length;
    const maxLength = inputElement.maxLength;
    feedbackElement.textContent = `${currentLength} / ${maxLength}`;
}
/**
 * 엑셀 업로드 관련 UI를 초기화하는 함수
 */
function resetExcelUpload() {
    const excelFileInput = document.getElementById('excelFileInput');
    const excelPreviewContainer = document.getElementById('excelPreviewContainer');
    const excelPreviewBody = document.getElementById('excelPreviewBody');
    const excelRecipientCount = document.getElementById('excelRecipientCount');

    if (excelFileInput) excelFileInput.value = '';
    if (excelPreviewContainer) excelPreviewContainer.style.display = 'none';
    if (excelPreviewBody) excelPreviewBody.innerHTML = '';
    if (excelRecipientCount) excelRecipientCount.textContent = '총 0건';
}

/**
 * 간편등록 관련 UI를 초기화하는 함수
 * @param {boolean} force - true일 경우 확인창 없이 강제로 초기화
 */
function resetSimpleRegistration(force = false) {
    const recipientListTextarea = document.getElementById('recipientList');
    // force가 true이거나, 내용이 있고 사용자가 확인을 누른 경우에만 실행
    // 버튼 클릭 로직이 showUnsavedChangesModal을 사용하도록 변경되었으므로, 이 함수의 confirm은 제거합니다.
    if (recipientListTextarea && (force || (recipientListTextarea.value.trim() !== '' && !force))) {
        recipientListTextarea.value = '';
        recipientListTextarea.dispatchEvent(new Event('input', { bubbles: true }));
    }
}

/**
 * 이메일 입력 필드의 유효성을 검사하고 피드백을 표시하는 함수
 */
function validateEmail() {
    const emailInput = document.getElementById('requesterEmail');
    const feedbackElement = document.getElementById('requesterEmail-feedback');
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (emailRegex.test(emailInput.value)) {
        feedbackElement.textContent = '유효한 이메일 형식입니다.';
        feedbackElement.style.color = 'green';
    } else if (emailInput.value === '') {
        // 이메일 필드가 비어있을 때는 원래 글자수 카운터로 되돌림
        updateCharCount(emailInput, feedbackElement);
        feedbackElement.style.color = ''; // 기본 색상으로
    } else {
        feedbackElement.textContent = '유효하지 않은 이메일 형식입니다.';
        feedbackElement.style.color = 'red';
    }
}

// 가상의 상품 데이터
const sampleProducts = [
    { name: "불고기 버거 세트", expiry: "60일", price: "5,000 / 7,000원", location: "전국 모든 매장" },
    { name: "새우 버거 세트", expiry: "60일", price: "4,500 / 6,500원", location: "전국 모든 매장" },
    { name: "아메리카노 (R)", expiry: "30일", price: "2,000 / 3,000원", location: "카페 A, 카페 B 전 지점" },
    { name: "영화 관람권 (1인)", expiry: "5년", price: "10,000 / 15,000원", location: "CGV, 롯데시네마, 메가박스" },
    { name: "치킨 콤보", expiry: "30일", price: "18,000 / 22,000원", location: "BBQ, BHC" },
    { name: "피자 L 사이즈", expiry: "30일", price: "25,000 / 30,000원", location: "도미노피자, 피자헛" },
    { name: "편의점 5천원권", expiry: "5년", price: "4,500 / 5,000원", location: "GS25, CU, 세븐일레븐" },
    { name: "베이커리 1만원권", expiry: "60일", price: "9,000 / 10,000원", location: "파리바게뜨, 뚜레쥬르" },
    { name: "아이스크림 파인트", expiry: "30일", price: "7,000 / 8,200원", location: "배스킨라빈스" },
    { name: "주유 5천원 할인권", expiry: "60일", price: "0 / 5,000원", location: "SK, GS칼텍스" },
    { name: "서점 1만원 도서상품권", expiry: "5년", price: "9,500 / 10,000원", location: "교보문고, 영풍문고" },
    { name: "음악 스트리밍 1개월권", expiry: "30일", price: "7,900 / 8,900원", location: "멜론, 지니뮤직" },
    { name: "OTT 1개월 이용권", expiry: "30일", price: "12,000 / 14,000원", location: "넷플릭스, 왓챠" },
    { name: "특급호텔 숙박권", expiry: "5년", price: "250,000 / 300,000원", location: "신라호텔, 롯데호텔" },
    { name: "백화점 5만원 상품권", expiry: "5년", price: "48,000 / 50,000원", location: "신세계, 롯데, 현대백화점" }
];

// Bootstrap Modal 인스턴스를 저장할 변수
let productModal;

/**
 * 상품 검색 버튼 클릭 시, 상품 목록을 모달에 표시하는 함수
 */
function searchProduct() {
    const tableBody = document.getElementById('product-list-table');
    // 기존 목록 초기화
    tableBody.innerHTML = '';

    // 가상 데이터로 목록 생성
    sampleProducts.forEach((product, index) => {
        const row = `<tr>
            <td>${product.name}</td>
            <td>${product.location}</td>
            <td>
                <button type="button" class="btn btn-primary btn-sm" onclick="selectProduct(${index})">선택</button>
            </td>
        </tr>`;
        tableBody.innerHTML += row;
    });

    // 모달을 띄웁니다.
    const modalElement = document.getElementById('productSearchModal');
    productModal = new bootstrap.Modal(modalElement);
    productModal.show();
}

/**
 * 모달에서 상품 선택 시, 해당 상품 정보를 메인 폼에 채워넣는 함수
 * @param {number} index - 선택한 상품의 sampleProducts 배열 인덱스
 */
function selectProduct(index) {
    const selectedProduct = sampleProducts[index];

    // 필드에 값 채우기
    document.getElementById("productName").value = selectedProduct.name;
    document.getElementById("product-expiry").value = selectedProduct.expiry;
    document.getElementById("product-price").value = selectedProduct.price;
    document.getElementById("product-location").value = selectedProduct.location;

    // 모달 닫기
    if (productModal) {
        productModal.hide();
    }
}

// 페이지를 떠나기 전 변경사항 확인
let allowNavigation = false; // 페이지 이동을 허용할지 여부

/**
 * 미저장 변경사항 확인 모달을 띄우는 함수
 * @param {function} onConfirm - '확인' 버튼 클릭 시 실행될 콜백 함수
 * @param {string} [message] - 모달에 표시할 메시지. 없으면 기본 메시지 사용.
 */
function showUnsavedChangesModal(onConfirm, message) {
    const modalEl = document.getElementById('unsavedChangesModal');
    if (!modalEl) {
        onConfirm();
        return;
    }

    const unsavedChangesModal = new bootstrap.Modal(modalEl);
    const confirmBtn = document.getElementById('confirmNavigateBtn');
    const modalBody = document.getElementById('unsavedChangesModalBody');
    const originalMessage = modalBody.dataset.originalMessage; // 기본 메시지 가져오기

    // 메시지 설정: 사용자 정의 메시지가 있으면 사용하고, 없으면 기본 메시지 사용
    if (message) {
        modalBody.innerHTML = message; // 줄바꿈(<br>)을 위해 innerHTML 사용
    } else {
        modalBody.innerHTML = originalMessage;
    }
    
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    newConfirmBtn.addEventListener('click', () => {
        onConfirm();
        unsavedChangesModal.hide();
    }, { once: true }); // 이벤트가 한 번만 실행되도록 설정

    unsavedChangesModal.show();
}

document.addEventListener('DOMContentLoaded', function() {
    // 모달의 기본 메시지를 data 속성에 저장
    const modalBody = document.getElementById('unsavedChangesModalBody');
    if (modalBody) {
        modalBody.dataset.originalMessage = modalBody.textContent;
    }

    // 모든 링크(<a>) 클릭을 가로채서 변경사항 확인
    document.body.addEventListener('click', function(e) {
        const link = e.target.closest('a');
        // 링크가 아니거나, 로그아웃 버튼이면 무시
        if (!link || link.id === 'logoutBtn') {
            return;
        }

        // 발송등록 페이지가 아니면 무시
        if (typeof isSendCouponFormDirty !== 'function') {
            return;
        }

        if (isSendCouponFormDirty()) {
            e.preventDefault(); // 기본 링크 이동 방지
            const targetUrl = link.href;
            showUnsavedChangesModal(() => {
                allowNavigation = true;
                window.location.href = targetUrl;
            });
        }
    });

    // 브라우저를 닫거나 새로고침할 때 경고
    window.addEventListener('beforeunload', function (e) {
        if (typeof isSendCouponFormDirty === 'function' && isSendCouponFormDirty() && !allowNavigation) {
            e.preventDefault();
            e.returnValue = ''; // 대부분의 브라우저에서 사용자 정의 메시지는 무시됨
        }
    });
});

/**
 * 발송등록 폼에 입력된 내용이 있는지 확인하는 함수
 * @returns {boolean} 내용이 있으면 true, 없으면 false
 */
 function isSendCouponFormDirty() {
    // 기본값이 설정된 필드와 그 값을 정의합니다.
    const defaultValues = {
        salesManager: '심재준',
        senderPhone: '16683551'
    };

    // 기본값이 없는 일반 필드 목록입니다.
    const otherFields = ['clientName', 'clientRequester', 'requesterPhone', 'requesterEmail', 'eventName', 'productName', 'mmsTitle', 'mmsContent', 'recipientList', 'excelFileInput'];

    // 1. 기본값이 있는 필드가 변경되었는지 확인합니다.
    for (const id in defaultValues) {
        const element = document.getElementById(id);
        if (element && element.value !== defaultValues[id]) return true;
    }

    // 2. 그 외 필드에 값이 입력되었는지 확인합니다.
    const dispatchInput = document.querySelector('#dispatchDateTime input');
    if (dispatchInput && dispatchInput.value) return true; // 발송 예약일시
    return otherFields.some(id => document.getElementById(id) && document.getElementById(id).value.trim() !== '');
}
