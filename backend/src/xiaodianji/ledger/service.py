from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from xiaodianji.confirmations.service import (
    ConfirmationConflict,
    FormalRecordRef,
)
from xiaodianji.customers.normalization import normalize_customer_name
from xiaodianji.models import (
    Customer,
    CustomerAlias,
    Payment,
    PendingConfirmation,
    Quote,
    QuoteItem,
    Transaction,
    TransactionItem,
)
from xiaodianji.schemas.record import (
    PaymentDraft,
    QuoteDraft,
    RecordDraft,
    TransactionDraft,
)


class LedgerNotFound(LookupError):
    pass


class LedgerService:
    async def create_from_confirmation(
        self,
        session: AsyncSession,
        confirmation: PendingConfirmation,
        draft: RecordDraft,
    ) -> FormalRecordRef:
        customer = await self._resolve_customer(
            session,
            confirmation.shop_id,
            draft.customer_id,
            draft.customer_name,
        )

        if isinstance(draft, TransactionDraft):
            transaction = Transaction(
                shop_id=confirmation.shop_id,
                customer_id=customer.id,
                occurred_at=draft.occurred_at,
                payment_status=draft.payment_status,
                total_amount=draft.total_amount,
                source_evidence_id=confirmation.source_evidence_id,
            )
            transaction.items = [
                TransactionItem(
                    product=item.product,
                    spec=item.spec,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
                for item in draft.items
            ]
            session.add(transaction)
            await session.flush()
            return FormalRecordRef("transaction", transaction.id)

        if isinstance(draft, QuoteDraft):
            quote = Quote(
                shop_id=confirmation.shop_id,
                customer_id=customer.id,
                quoted_at=draft.quoted_at,
                total_amount=draft.total_amount,
                source_evidence_id=confirmation.source_evidence_id,
            )
            quote.items = [
                QuoteItem(
                    product=item.product,
                    spec=item.spec,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
                for item in draft.items
            ]
            session.add(quote)
            await session.flush()
            return FormalRecordRef("quote", quote.id)

        if isinstance(draft, PaymentDraft):
            payment = Payment(
                shop_id=confirmation.shop_id,
                customer_id=customer.id,
                amount=draft.amount,
                paid_at=draft.paid_at,
                source_evidence_id=confirmation.source_evidence_id,
            )
            session.add(payment)
            await session.flush()
            return FormalRecordRef("payment", payment.id)

        raise TypeError(f"unsupported record draft: {type(draft)!r}")

    async def get_transaction(
        self,
        session: AsyncSession,
        shop_id: UUID,
        transaction_id: UUID,
    ) -> Transaction:
        transaction = await session.scalar(
            select(Transaction)
            .where(
                Transaction.id == transaction_id,
                Transaction.shop_id == shop_id,
            )
            .options(selectinload(Transaction.items))
        )
        if transaction is None:
            raise LedgerNotFound(str(transaction_id))
        return transaction

    async def get_quote(
        self,
        session: AsyncSession,
        shop_id: UUID,
        quote_id: UUID,
    ) -> Quote:
        quote = await session.scalar(
            select(Quote)
            .where(Quote.id == quote_id, Quote.shop_id == shop_id)
            .options(selectinload(Quote.items))
        )
        if quote is None:
            raise LedgerNotFound(str(quote_id))
        return quote

    async def _resolve_customer(
        self,
        session: AsyncSession,
        shop_id: UUID,
        customer_id: UUID | None,
        customer_name: str,
    ) -> Customer:
        if customer_id is not None:
            customer = await session.get(Customer, customer_id)
            if customer is None or customer.shop_id != shop_id:
                raise ConfirmationConflict("customer does not belong to this shop")
            return customer

        normalized_name = normalize_customer_name(customer_name)
        matches = (
            await session.scalars(
                select(Customer)
                .outerjoin(CustomerAlias)
                .where(
                    Customer.shop_id == shop_id,
                    or_(
                        Customer.normalized_name == normalized_name,
                        CustomerAlias.normalized_alias == normalized_name,
                    ),
                )
                .distinct()
            )
        ).all()
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ConfirmationConflict(
                "customer name matches multiple customers; select one explicitly"
            )

        customer = Customer(
            shop_id=shop_id,
            name=customer_name,
            normalized_name=normalized_name,
        )
        session.add(customer)
        await session.flush()
        return customer

