from argparse import ArgumentParser
from typing import Optional

import torch
import wandb
from torch import nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from src.data_processing.image_dataset import Cifar10Dataset
from src.evaluation.evaluate_classifier import evaluate_classifier
from src.modules.autoencoder import AutoEncoder
from src.modules.classifier import Classifier
from src.training.add_training_arguments import add_training_arguments


def train_classifier(
        encoder: nn.Module,
        channels: int = 256,
        epochs: int = 100,
        lr: float = 3e-4,
        train_batch_size: int = 16,
        test_batch_size: int = 16,
        to_evaluate: bool = True,
        wandb_login: Optional[str] = None,
        save_path: Optional[str] = None,
        seed: int = 0,
):
    torch.manual_seed(seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    classifier = Classifier(in_channels=channels)
    classifier.to(device)

    encoder.to(device)

    train_loader = DataLoader(Cifar10Dataset('train'), batch_size=train_batch_size)

    if wandb_login:
        wandb.init(project='autoencoder', entity=wandb_login)
        wandb.config = {
            'epochs': epochs,
            'lr': lr,
            'train_batch_size': train_batch_size,
            'test_batch_size': test_batch_size,
            'save_path': save_path
        }

    optimizer = torch.optim.Adam(classifier.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    with tqdm(total=epochs, desc='training') as bar:
        for epoch in range(epochs):
            epoch_loss = 0
            for batch in train_loader:
                optimizer.zero_grad()

                img, labels = batch['img'].to(device), batch['label'].to(device)
                hidden_representation = encoder(img)
                outputs = classifier(hidden_representation)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            epoch_loss /= len(train_loader)
            bar.update(1)
            print(epoch_loss)
            if wandb_login:
                wandb.log({'classifier_loss': epoch_loss})

            if save_path:
                classifier.save(save_path)

    if to_evaluate:
        evaluate_classifier(
            classifier=classifier,
            encoder=encoder,
            test_batch_size=test_batch_size,
            wandb_login=wandb_login
        )


def main():
    parser = ArgumentParser()
    parser = add_training_arguments(parser)
    parser.add_argument('autoencoder_model_path', help='path for autoencoder model', type=str)
    args = parser.parse_args()
    autoencoder = AutoEncoder().load_model(args['path'])
    encoder = autoencoder.get_encoder()
    train_classifier(
        encoder=encoder,
        epochs=args['epochs'],
        lr=args['lr'],
        train_batch_size=args['train_batch_size'],
        test_batch_size=args['test_batch_size'],
        to_evaluate=args['to_evaluate'],
        wandb_login=args['wandb_login'],
        save_path=args['save_path'],
        seed=args['seed']
    )


if __name__ == '__main__':
    main()