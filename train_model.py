#!/usr/bin/env python3
"""
Train the fraud detection ML model.

This script:
1. Loads transaction data from the database
2. Trains an Isolation Forest model
3. Evaluates performance
4. Saves the model to disk

Usage:
    python train_model.py [--contamination 0.05]
"""

import logging
import argparse
from src.models import FraudDetectionModel
from src.database import Database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Train fraud detection model')
    parser.add_argument(
        '--contamination',
        type=float,
        default=0.05,
        help='Expected fraud rate (0.02-0.10), default 0.05 (5%%)'
    )
    args = parser.parse_args()

    # Initialize database connection
    Database.get_connection()

    # Train model
    model = FraudDetectionModel()
    metrics = model.train(contamination=args.contamination)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Model Version: {model.model_version}")
    logger.info(f"Features Used: {len(model.feature_names)}")
    logger.info(f"Contamination: {args.contamination}")
    logger.info(f"\nPerformance:")
    logger.info(f"  Accuracy:  {metrics['accuracy']:.2%}")
    logger.info(f"  Precision: {metrics['precision']:.2%}")
    logger.info(f"  Recall:    {metrics['recall']:.2%}")
    logger.info(f"  F1 Score:  {metrics['f1_score']:.2%}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
