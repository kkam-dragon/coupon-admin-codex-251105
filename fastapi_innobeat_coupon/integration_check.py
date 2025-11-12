from __future__ import annotations

import argparse

from app.services import coufun_service


def main() -> None:
    parser = argparse.ArgumentParser(description="COUFUN API 연동 점검 스크립트")
    parser.add_argument("--status", nargs=2, metavar=("GOODS_ID", "BARCODE"), help="쿠폰 상태 조회")
    parser.add_argument("--goods", action="store_true", help="상품 목록 조회")
    parser.add_argument("--issue", metavar="GOODS_ID", help="테스트 발급 (mock 모드에서만 사용)")
    args = parser.parse_args()

    if args.goods:
        goods = coufun_service.fetch_goods_list()
        print("상품 수:", len(goods.products))
        for product in goods.products[:5]:
            print(product.goods_id, product.name, product.valid_days)

    if args.status:
        goods_id, barcode = args.status
        status = coufun_service.get_coupon_status(goods_id, barcode)
        print("쿠폰 상태:", status.status, status.status_label)

    if args.issue:
        result = coufun_service.issue_coupon(goods_id=args.issue, tr_id="INTEGRATION_TEST")
        print("발급 완료:", result.order_id, result.valid_end_date)


if __name__ == "__main__":
    main()
