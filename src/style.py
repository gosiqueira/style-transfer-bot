import torch
from matplotlib import pyplot as plt
from torchvision import models, transforms

from utils import *


def transfer(style_img, content_img):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # desired size of the output image
    imsize = 512 if torch.cuda.is_available() else 128  # use small size if no gpu

    loader = transforms.Compose([
        transforms.Resize(imsize),  # scale imported image
        transforms.ToTensor()       # transform it into a torch tensor
    ])  

    def prepare_image(image):
        image = loader(image).unsqueeze(0)
        return image.to(device, torch.float)

    style_img, content_img = prepare_image(style_img), prepare_image(content_img)

    assert style_img.size() == content_img.size(), 'we need to import style and content images of the same size'

    cnn = models.vgg19(pretrained=True).features.to(device).eval()
    cnn_normalization_mean = torch.tensor([0.485, 0.456, 0.406]).to(device)
    cnn_normalization_std = torch.tensor([0.229, 0.224, 0.225]).to(device)


    print('Building the style transfer model..')

    model, style_losses, content_losses = get_style_model_and_losses(cnn,
        cnn_normalization_mean, cnn_normalization_std, style_img, content_img)
    optimizer = get_input_optimizer(content_img)

    num_steps      = 300
    style_weight   = 1000000
    content_weight = 1


    print('Optimizing..')
    run = [0]
    while run[0] <= num_steps:

        def closure():
            # correct the values of updated input image
            content_img.data.clamp_(0, 1)

            optimizer.zero_grad()
            model(content_img)
            style_score = 0
            content_score = 0

            for sl in style_losses:
                style_score += sl.loss
            for cl in content_losses:
                content_score += cl.loss

            style_score *= style_weight
            content_score *= content_weight

            loss = style_score + content_score
            loss.backward()

            run[0] += 1
            if run[0] % 50 == 0:
                print('run {}:'.format(run[0]))
                print('Style Loss : {:4f} Content Loss: {:4f}'.format(
                    style_score.item(), content_score.item()))
                print()

            return style_score + content_score

        optimizer.step(closure)

    # a last correction...
    content_img.data.clamp_(0, 1)

    return content_img


def main():
    style_img   = image_loader('data/picasso.jpg')
    content_img = image_loader('data/dancing.jpg')

    plt.figure()
    imshow(style_img, title='Style Image')

    plt.figure()
    imshow(content_img, title='Content Image')

    plt.show()

    resulting_img = transfer(style_img, content_img)

    plt.figure()
    imshow(resulting_img, title='Result Image')
    plt.ioff()
    plt.show()


if __name__ == '__main__':
    main()
